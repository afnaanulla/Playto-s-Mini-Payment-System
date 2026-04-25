import uuid
from django.db import models, transaction
from django.db.models import Sum, Q
from django.utils.translation import gettext_lazy as _


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    bank_account_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def calculate_balance(self):
        """
        Calculates the available balance using SQL aggregation.
        Available = Credits - Held Debits - Settled Debits

        Held Debits = DR entries linked to pending/processing payouts (temporarily unavailable)
        Settled Debits = DR entries linked to completed payouts (permanently spent)

        This distinction is critical: when a payout is created, funds are 'held' (not yet spent).
        Only when the payout completes do the funds become 'settled' (actually spent).
        """
        return self.calculate_balance_split()['available_paise']

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


class Payout(models.Model):
    # NOTE: We are using Django's `TextChoices` which acts as a native Python Enum.
    # This enforces strict database-level validation so no magic strings (like 'PENDNIG') can be saved.
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='payouts')
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True  # Index for filtering by status
    )
    idempotency_key = models.UUIDField(db_index=True)  # Index for idempotency lookups
    failure_reason = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True, db_index=True)  # Index for retry queries
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['merchant', 'idempotency_key'], name='unique_payout_per_merchant')
        ]
        indexes = [
            models.Index(fields=['status', 'last_attempted_at']),  # For retry_stuck_payouts query
            models.Index(fields=['merchant', 'created_at']),  # For merchant payout history
            models.Index(fields=['status']),  # For status filtering
        ]

    def __str__(self):
        return f"Payout {self.id} - {self.status}"

    def transition_to(self, new_status):
        """
        State machine transition validator.
        Prevents illegal state transitions like failed->completed or completed->pending.
        Raises ValueError on invalid transition.
        """
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


class IdempotencyKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE)
    key = models.UUIDField()
    response_body = models.JSONField(null=True, blank=True)  # null = in-flight
    response_status = models.PositiveSmallIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)  # Index for cleanup queries

    class Meta:
        unique_together = [('merchant', 'key')]
        indexes = [
            models.Index(fields=['expires_at']),  # For expiry cleanup job
        ]

    def __str__(self):
        return f"IdempotencyKey {self.key} - {'completed' if self.response_body else 'in-flight'}"


class LedgerEntry(models.Model):
    # Strict Enum for Ledger Entries.
    # Using concise values ('CR' and 'DR') instead of long strings saves massive disk space at scale.
    class EntryType(models.TextChoices):
        CREDIT = 'CR', _('Credit')
        DEBIT = 'DR', _('Debit')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='ledger_entries')
    amount_paise = models.BigIntegerField()
    entry_type = models.CharField(max_length=2, choices=EntryType.choices)
    description = models.CharField(max_length=500, blank=True)
    payout = models.ForeignKey(Payout, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_entries')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['merchant', 'created_at']),  # For merchant ledger history
            models.Index(fields=['merchant', 'entry_type']),  # For balance calculations
        ]

    def __str__(self):
        return f"{self.entry_type} - {self.amount_paise} paise"
