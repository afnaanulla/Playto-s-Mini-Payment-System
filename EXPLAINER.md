# EXPLAINER.md — Playto Payout Engine

## 1. The Ledger
### Balance Calculation Query
```python
def calculate_balance_split(self):
    aggregates = self.ledger_entries.aggregate(
        credits=Sum('amount_paise', filter=Q(entry_type='CR'), default=0),
        completed_debits=Sum('amount_paise', filter=Q(entry_type='DR', payout__status='COMPLETED'), default=0),
        failed_debits=Sum('amount_paise', filter=Q(entry_type='DR', payout__status='FAILED'), default=0),
        held_debits=Sum('amount_paise', filter=Q(entry_type='DR', payout__status__in=['PENDING', 'PROCESSING']), default=0)
    )
    credits = aggregates['credits'] or 0
    held = aggregates['held_debits'] or 0
    completed = aggregates['completed_debits'] or 0
    failed = aggregates['failed_debits'] or 0
    return {
        'available_paise': credits - held - completed - failed,
        'held_paise': held,
        'total_paid_out': completed,
    }
```

### Why model credits and debits this way?
We model balance through immutable `LedgerEntry` records using a double-entry logic rather than a single mutable balance column. The key reasons are:
1. **Immutable Audit Trail:** We can reconstruct the balance at any point in time. It provides a source of truth that cannot drift.
2. **Handling Held vs Settled:** By splitting credits and debits and factoring in payout statuses, we accurately model the lifecycle of funds. A DR entry linked to a `PENDING`/`PROCESSING` payout holds the funds (making them unavailable) without classifying them as permanently spent (settled). If a payout fails, a compensatory CR entry is atomically created, refunding the exact amount without ever altering the original immutable DR record.

## 2. The Lock
### Code that prevents concurrent overdraw
```python
with transaction.atomic():
    # Lock the merchant row until transaction completes
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)
    
    # Check balance inside transaction
    current_balance = merchant.calculate_balance()

    if current_balance < amount_paise:
        # Reject with 422
```

### Database primitive it relies on
This implementation relies on PostgreSQL's `SELECT FOR UPDATE` primitive. When Thread A calls `select_for_update()`, it acquires an exclusive row-level lock on that specific `Merchant` record. If Thread B arrives concurrently for the exact same merchant, it blocks at the database level and waits for Thread A's `transaction.atomic()` block to commit. Once Thread A finishes and releases the lock, Thread B unblocks, recalculates the true balance (which now factors in Thread A's successful debit), and properly evaluates if there are enough funds remaining. This completely eliminates the classic "check-then-deduct" race condition.

## 3. The Idempotency
### How the system knows it has seen a key before
We maintain an `IdempotencyKey` table with a `unique_together` constraint on `(merchant, key)`. Every request validates this combination inside an atomic block:
```python
try:
    idem_record = IdempotencyKey.objects.get(merchant=merchant, key=idem_key_uuid)
```

### What happens if the first request is in flight when the second arrives?
Because our idempotency check happens inside the same atomic block and under the same `select_for_update()` lock that processes the payout, a concurrent second request for the same merchant will actually block until the first completes. 
If the first request was somehow "in flight" across different API boundaries or the lock was not blocking, it would hit our strict flight check logic:
```python
elif idem_record.response_body is not None:
    return Response(idem_record.response_body, status=idem_record.response_status)
else:
    # First request still in flight
    return Response(
        {"error": "Request with this idempotency key is already in progress"}, 
        status=status.HTTP_409_CONFLICT
    )
```
The first request creates the `IdempotencyKey` with `response_body=None`. Any request finding it in this null state correctly returns a 409 Conflict without causing a duplicate transaction.

## 4. The State Machine
### Where is failed-to-completed blocked?
It is blocked inside `transition_to` in the `Payout` model (`payouts/models.py`), utilizing a hardcoded dictionary mapping of legal state transitions.

```python
def transition_to(self, new_status):
    VALID_TRANSITIONS = {
        self.Status.PENDING: [self.Status.PROCESSING],
        self.Status.PROCESSING: [self.Status.COMPLETED, self.Status.FAILED, self.Status.PENDING],
        self.Status.COMPLETED: [],  # Terminal state
        self.Status.FAILED: [],  # Terminal state
    }
    allowed = VALID_TRANSITIONS.get(self.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Illegal state transition: {self.status} -> {new_status}. "
            f"Allowed from {self.status}: {allowed}"
        )
    self.status = new_status
    self.save(update_fields=['status', 'updated_at'])
```
Because `self.Status.FAILED` has an empty list of allowed transitions (`[]`), attempting to set the status to `COMPLETED` when it is already `FAILED` will immediately throw a `ValueError`. This exception prevents any further DB commits inside the transaction block.

## 5. The AI Audit
### What it gave me (wrong)
When assisting with the `PayoutCreateView`, the AI initially wrote the idempotency logic with a check-then-create race condition and outside the lock:

```python
try:
    idem_record = IdempotencyKey.objects.get(merchant_id=merchant_id, key=idem_key_uuid)
except IdempotencyKey.DoesNotExist:
    # AI blindly created it outside the transaction!
    idem_record = IdempotencyKey.objects.create(
        merchant_id=merchant_id, key=idem_key_uuid, response_body=None, ...
    )

# ... later ...
with transaction.atomic():
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)
    # payout logic ...
```

### What I caught (The Bug)
This approach created a massive race condition. Two simultaneous requests with the same idempotency key would both pass the `DoesNotExist` check and attempt to `create()`. One would succeed, while the other would throw an `IntegrityError` due to the unique database constraint, returning an ugly 500. Furthermore, because the creation was completely decoupled from the atomic processing block, it risked leaving orphaned idempotency keys if the main transaction failed later.

### What I replaced it with
I rewrote the view so the idempotency check, the creation of the `IdempotencyKey` record, the balance calculation, and the payout processing ALL happen sequentially inside the single `transaction.atomic()` block, protected by the `Merchant.objects.select_for_update()` lock. This guarantees strict serialization for concurrent duplicate requests.

```python
with transaction.atomic():
    # 1. Lock the merchant row to serialize all traffic
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)

    # 2. Check and handle Idempotency inside the transaction safely
    try:
        idem_record = IdempotencyKey.objects.get(merchant=merchant, key=idem_key_uuid)
        if idem_record.response_body is not None:
            return Response(idem_record.response_body, status=idem_record.response_status)
        else:
            return Response({"error": "Request in progress"}, status=status.HTTP_409_CONFLICT)
    except IdempotencyKey.DoesNotExist:
        idem_record = IdempotencyKey.objects.create(...)
    
    # 3. Calculate balance and create payout...
```
