# 🎤 Playto Payout Engine - Interview Demo Guide

This document is your **cheat sheet** for the interview. It contains the exact steps, commands, and talking points to demonstrate all 5 edge cases to the CTO.

---

## 🏗️ 0. Setup before the Interview
Before jumping into the demo, make sure your environment is clean and running.

**Open 3 Terminal Windows:**
1. **Terminal 1 (Django):** `python manage.py runserver`
2. **Terminal 2 (Celery):** `docker-compose logs -f worker beat` (To show background jobs)
3. **Terminal 3 (Commands):** Leave this open to run your tests and seed data.

**Reset the database so you have exactly 10,000 INR (1,000,000 paise):**
```bash
python manage.py seed_data
```

**How to find IDs for testing:**
- **Merchant ID:** Open `http://localhost:8000/api/v1/merchants` in your browser or run a GET request to see all seeded merchants.
- **Transaction (Payout) ID:** This is returned in the response when you create a payout. You can also view a merchant's history at `http://localhost:8000/api/v1/merchants/<merchant_id>/payouts`.

**🛠️ How to Create a New Merchant & Add Funds manually:**
If the CTO asks you to create a completely new merchant and fund them on the spot, open Terminal 3 and run `python manage.py shell`, then paste this:
```python
from payouts.models import Merchant, LedgerEntry

# 1. Create the new Merchant
merchant = Merchant.objects.create(name="Interview Startup", bank_account_id="ICIC9999")

# 2. Add 50,000 INR (5,000,000 paise) via a Credit Ledger Entry
LedgerEntry.objects.create(
    merchant=merchant, 
    amount_paise=5000000, 
    entry_type='CR', 
    description="Initial funding deposit"
)

print(f"Created! New Merchant ID: {merchant.id}")
```

---

## 🛡️ Demo 1: The Race Condition (Concurrency)
**The Problem:** If a user clicks "Withdraw" twice very fast, it could bypass the balance check and overdraw the account.
**The Fix:** PostgreSQL `SELECT FOR UPDATE` row-level locking.

**How to show it:**
1. In Terminal 3, run:
   ```bash
   python concurrency_test.py
   ```
2. **What to point out to the interviewer:**
   - *"As you can see, I fired two threads simultaneously asking for 6,000 INR."*
   - *"Only one succeeded (Status 201), and the other failed (Status 422: Insufficient funds)."*
3. **Show the Code (`payouts/views.py` Line 60):**
   - Show them the line: `merchant = Merchant.objects.select_for_update().get(id=merchant_id)`
   - Tell them: *"This acquires a strict database lock. The second request physically has to wait for the first transaction to finish. By the time it unblocks, the balance is recalculated as 4,000, so it correctly rejects the 6,000 request."*

---

## 🔄 Demo 2: Idempotency (Duplicate Prevention)
**The Problem:** If a network drops and a client retries the same request, they shouldn't be charged twice.
**The Fix:** Storing responses in the `IdempotencyKey` table inside the same transaction block.

**How to show it:**
1. This is automatically demonstrated right after the Race Condition test in `concurrency_test.py`.
2. **What to point out:**
   - *"Look at the terminal output for the Idempotency test. It sent two requests with the exact same UUID."*
   - *"Notice how it returned `Status 201` for both, but the `Payout ID` is exactly the same! It intercepted the second request and returned the cached response without hitting the ledger twice."*

---

## ⏱️ Demo 3: The Stuck Payout & Atomic Refund
**The Problem:** What if the bank API goes down and times out? The money shouldn't be lost forever.
**The Fix:** Exponential backoff retries via Celery Beat, and an Atomic Ledger Refund.

**How to show it:**
1. Open `payouts/tasks.py` and go to line 59.
2. Tell the interviewer: *"I'm going to simulate a dead bank API by forcing a timeout."*
3. Change the code to:
   ```python
   # FOR TESTING RETRY EDGE CASE: We force the bank to 'timeout' every time
   outcome = 'timeout'
   ```
4. **Restart your workers** so they get the new code:
   ```bash
   docker-compose restart worker beat
   ```
5. Go to your **React Dashboard** (`http://localhost:5173`).
   - Create a payout for 500 INR.
   - Point out to the interviewer: *"The 500 INR is immediately deducted from Available Balance, and the status is `PROCESSING`."*
6. **Show Terminal 2 (Celery Logs):**
   - Wait 30 seconds. Point to the screen when Celery Beat logs: *`Payout reset to PENDING, retrying in 30s`*.
   - Explain: *"My background worker detected the stuck payout and is retrying it with an exponential backoff (30s, 60s, 120s)."*
7. **The Refund:**
   - Tell them that after 3 attempts, it marks it as `FAILED`. 
   - Tell them to watch the React Dashboard. When it finally fails, the 500 INR will instantly reappear in the Available Balance.
   - **Show the Code (`tasks.py` Line 131):** Show them the `LedgerEntry.objects.create(..., entry_type=CREDIT)` that automatically refunds the money.
8. **IMPORTANT: Change `outcome = 'timeout'` back to the random choice in `tasks.py` when you are done!**

---

## 🛑 Demo 4: State Machine Hack (Time-Travel)
**The Problem:** A buggy script or attacker tries to change a `FAILED` payout back to `COMPLETED` to steal money.
**The Fix:** A strict Python-level state machine.

**How to show it:**
1. Open your Django Shell in Terminal 3:
   ```bash
   python manage.py shell
   ```
2. Paste this exact script to try and "hack" a completed payout:
   ```python
   from payouts.models import Payout
   
   # Grab the very first payout in the database, no matter what status it is
   p = Payout.objects.first()
   print(f"Hacking payout: {p.id} with status: {p.status}")
   
   # Let's try to illegally change it to something it shouldn't be allowed to change to!
   if p.status == 'COMPLETED':
       p.transition_to('PENDING')
   elif p.status == 'FAILED':
       p.transition_to('COMPLETED')
   elif p.status == 'PENDING':
       p.transition_to('COMPLETED') # Must go to PROCESSING first!
   else:
       p.transition_to('PENDING')
   ```
3. **What to point out:**
   - The shell will instantly crash with a `ValueError: Illegal state transition`.
   - Tell the interviewer: *"The core model natively rejects illegal transitions. Because this throws an error, the database transaction aborts, making it mathematically impossible to force a bad state."*

---

## 🤖 Demo 5: The AI Audit
**The Problem:** They asked you to explain where an AI made a mistake.
**The Fix:** Fixing the "Check-then-act" pattern and a hidden Django-Celery Race Condition.

**How to explain it:**
- Open `EXPLAINER.md` to Section 5.
- Tell them: *"The AI originally made two massive concurrency mistakes that I had to fix."*
- *"**Mistake 1:** It wrote the Idempotency check outside of the database lock using `get_or_create`. I moved it inside the `transaction.atomic()` block under the `select_for_update` lock so the second request literally waits in line at the database level."*
- *"**Mistake 2:** It called `process_payout.delay()` inside the database transaction. This caused a classic race condition where the Celery worker picked up the job before the database even committed the Payout, causing the worker to crash because it couldn't find the record. I fixed this by using `transaction.on_commit()`, which guarantees the task is only queued after the data is safely on disk."*

---

## 🚫 Demo 6: API Payload Validation (Edge Cases)
**The Problem:** Hackers or bad client code sending malformed data (negative money, missing headers).
**The Fix:** Django REST Framework strict serializers and header validation.

**How to show it:**
1. Open **Postman**, **cURL**, or any API testing tool.
2. Tell them: *"Let's see what happens if someone tries to trick the system."*

**Sample Payload to keep handy for testing:**
```json
{
  "merchant_id": "900f43e4-42b9-4635-9ec2-f59dee9528d4",
  "amount_paise": 999999999,
  "bank_account_id": "HDFC000123"
}
```

3. **Missing Idempotency Key:**
   - Send a `POST` to `http://localhost:8000/api/v1/payouts` with a valid body but NO `Idempotency-Key` header.
   - Show the result: `400 Bad Request: Idempotency-Key header is required`.
4. **Negative Amounts:**
   - Send `-5000` as the `amount_paise`.
   - Show the result: `400 Bad Request` (blocked by the Serializer `min_value` rule).
5. **Astronomical Amounts:**
   - Request `9999999999` paise.
   - Show the result: `422 Unprocessable Entity: Insufficient funds`.
6. **Invalid Idempotency Key Format (Not a UUID):**
   - Send `Idempotency-Key: this-is-not-a-uuid` in the headers.
   - Show the result: `400 Bad Request: Invalid Idempotency-Key format. Must be UUID.`
7. **Unknown Merchant ID:**
   - Send a randomly generated UUID for `merchant_id` that doesn't exist in the database.
   - Show the result: `404 Not Found: Merchant not found`.

---

## ⏳ Demo 8: Idempotency Key Expiry (24 Hour Rule)
**The Problem:** The challenge strictly requires Idempotency Keys to expire after 24 hours. After this period, sending the same key should trigger a *brand new* payout rather than returning the cached response.
**The Fix:** We store an `expires_at` timestamp on the `IdempotencyKey` record and check if it has expired before returning the cached data.

**How to show it:**
1. Make a successful payout request in Postman/cURL with a brand new Idempotency Key.
2. Open the Django Shell in Terminal 3 (`python manage.py shell`).
3. Run this script to simulate "time-travel" by moving the key's expiration date 25 hours into the past:
   ```python
   from payouts.models import IdempotencyKey
   from django.utils import timezone
   import datetime

   # Grab the most recent key
   key = IdempotencyKey.objects.latest('created_at') 
   key.expires_at = timezone.now() - datetime.timedelta(hours=25)
   key.save()
   print(f"Key {key.key} artificially expired!")
   ```
4. Go back to Postman and resend the *exact same request* with the *exact same Idempotency Key*.
5. **What to point out to the CTO:** 
   - *"Watch the `Payout ID` in the response. Because the original key was older than 24 hours, the system detected it, deleted the expired cache, and processed a completely new payout instead of returning the cached response."*

---

## 🧮 Demo 7: Money Integrity & Database Aggregation
**The Problem:** Calculating balances in Python by looping over rows can cause desyncs and memory leaks. Using Floats for money causes rounding errors.
**The Fix:** `BigIntegerField` and SQL Aggregation.

**How to show it:**
1. **Show the Code (`payouts/models.py`):**
   - Point to `amount_paise = models.BigIntegerField()`.
   - Explain: *"I strictly used BigIntegerField and stored everything in paise to completely eliminate floating-point rounding errors."*
2. **Show the Aggregation (`payouts/models.py` Line 40):**
   - Point to `calculate_balance_split()` where it uses Django's `Sum('amount_paise')`.
   - Explain: *"I never calculate the balance in Python. I use SQL aggregation to sum all credits and subtract all debits directly inside the database. This guarantees the mathematical invariant that the sum of credits minus debits perfectly equals the displayed balance."*

---

## 🚦 Demo 9: Idempotency on Business Logic Failures (The 422 Cache)
**The Problem:** If a user tries to withdraw more money than they have, it fails. But what if they retry the exact same failing request? Standard systems might run the heavy balance calculation again.
**The Fix:** Caching business logic errors (like `422 Insufficient Funds`) inside the `IdempotencyKey` record.

**How to show it:**
1. Send a `POST` request using Postman with an `Idempotency-Key` for an amount much larger than the available balance (e.g., 9,999,999).
2. Note the response: `422 Unprocessable Entity` with the "Insufficient funds" error.
3. Immediately send the exact same request again.
4. **What to point out:**
   - *"The second request didn't even run the balance calculation. Because the first request failed due to a business logic error (Insufficient funds), we cached that exact `422` error response in the Idempotency Key table."*
   - *"This saves database compute resources and ensures strict deterministic behavior."*

---

## 💣 Demo 10: Graceful Failure on Unhandled Exceptions (The 500 Rollback)
**The Problem:** If a completely unhandled exception occurs (e.g., the server runs out of memory or a database node dies mid-request), the Idempotency Key might get stuck "in-flight" forever, preventing the user from ever retrying.
**The Fix:** Relying on the `transaction.atomic()` rollback.

**How to show it:**
1. Point to the `except Exception as e:` block at the very end of `payouts/views.py`.
2. **What to point out:**
   - *"You'll notice there is no manual `idem_record.delete()` here anymore."*
   - *"Because the entire request logic (including Idempotency Key creation) is wrapped inside a single `transaction.atomic()` block, any unhandled Python exception will cause the database to roll back the entire transaction instantly."*
   - *"This means the Idempotency Key disappears as if it never existed, allowing the client to safely retry the request once the system is healthy again."*


from payouts.models import Merchant, LedgerEntry

# 1. Create the new Merchant
merchant = Merchant.objects.create(name="Interview Startup", bank_account_id="ICIC9999")

# 2. Add 50,000 INR (5,000,000 paise) via a Credit Ledger Entry
LedgerEntry.objects.create(
    merchant=merchant, 
    amount_paise=5000000, 
    entry_type='CR', 
    description="Initial funding deposit"
)

print(f"Created! New Merchant ID: {merchant.id}")
