import os
import time
import random
import logging

logger = logging.getLogger(__name__)
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Payout, LedgerEntry

# Configurable bank simulation delay (for testing vs production)
# Set BANK_SIMULATION_DELAY=0 in production for instant processing
BANK_SIMULATION_DELAY = float(os.environ.get('BANK_SIMULATION_DELAY', '0.5'))


@shared_task(bind=True, max_retries=0)
def process_payout(self, payout_id):
    """
    Simulates a bank API call and updates payout state.

    Simulated outcomes:
    - 70% Success: Payout completes, funds are settled
    - 20% Failure: Payout fails, funds are refunded via credit entry
    - 10% Timeout: Task exits without updating state (stuck in PROCESSING)
                   The retry_stuck_payouts beat task will retry after 30s

    State Machine:
    PENDING -> PROCESSING -> COMPLETED
                          -> FAILED (with refund)
    """
    try:
        payout = Payout.objects.get(id=payout_id)
    except Payout.DoesNotExist:
        logger.info(f"Payout {payout_id} not found, skipping")
        return

    # Guard: only process pending payouts
    if payout.status != Payout.Status.PENDING:
        logger.info(f"Payout {payout_id} is not PENDING (status={payout.status}), skipping")
        return

    with transaction.atomic():
        # Re-fetch with lock to prevent concurrent task execution
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status != Payout.Status.PENDING:
            # Another worker already picked up this payout
            logger.info(f"Payout {payout_id} was picked up by another worker, skipping")
            return

        payout.attempt_count += 1
        payout.last_attempted_at = timezone.now()
        payout.save(update_fields=['attempt_count', 'last_attempted_at'])
        payout.transition_to(Payout.Status.PROCESSING)

    # --- Simulate Bank API Call (outside transaction) ---
    # In production, this would be an actual HTTP call to the bank's API
    outcome = random.choices(
        ['success', 'failure', 'timeout'],
        weights=[70, 20, 10]
    )[0]

    # Simulate network latency (configurable)
    time.sleep(BANK_SIMULATION_DELAY)

    if outcome == 'timeout':
        # Simply exit without updating state.
        # The payout remains in PROCESSING and will be picked up by retry_stuck_payouts.
        logger.info(f"Payout {payout_id} timed out (simulated), attempt {payout.attempt_count}")
        return

    with transaction.atomic():
        # Re-fetch with lock for final status update
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if outcome == 'success':
            payout.transition_to(Payout.Status.COMPLETED)
            logger.info(f"Payout {payout_id} completed successfully")
            # Funds are already held in DR entry. No further ledger entry needed.
            # The held DR entry is now considered "settled" because payout status is COMPLETED.

        elif outcome == 'failure':
            payout.failure_reason = "Bank declined the transfer"
            payout.save(update_fields=['failure_reason'])
            payout.transition_to(Payout.Status.FAILED)
            logger.info(f"Payout {payout_id} failed: {payout.failure_reason}")

            # ATOMICALLY Refund: create a credit to return held funds
            # This ensures funds are never lost - if transaction fails, both state change
            # and refund roll back together.
            LedgerEntry.objects.create(
                merchant=payout.merchant,
                amount_paise=payout.amount_paise,
                entry_type=LedgerEntry.EntryType.CREDIT,
                payout=payout,
                description=f"Refund for failed payout {payout.id}"
            )


@shared_task
def retry_stuck_payouts():
    """
    Runs periodically (every 15 seconds via Celery Beat) to find payouts
    stuck in 'PROCESSING' for more than 30 seconds.

    Retry logic with exponential backoff:
    - Attempts 1-2: Reset to PENDING and re-enqueue with delay (30s * 2^attempt)
    - Attempt 3+: Mark as FAILED and refund funds

    Uses select_for_update(skip_locked=True) to avoid multiple workers
    processing the same payout.
    """
    # Fetch IDs without lock first to avoid large locking transactions
    cutoff = timezone.now() - timezone.timedelta(seconds=30)
    stuck_payout_ids = list(Payout.objects.filter(
        status=Payout.Status.PROCESSING,
        last_attempted_at__lt=cutoff
    ).values_list('id', flat=True)[:50])

    for pid in stuck_payout_ids:
        with transaction.atomic():
            payout = Payout.objects.select_for_update(skip_locked=True).filter(id=pid).first()
            if not payout or payout.status != Payout.Status.PROCESSING:
                continue

            if payout.attempt_count >= 3:
                # Max retry attempts exceeded - mark as failed and refund
                payout.failure_reason = 'Max retry attempts exceeded (3)'
                payout.save(update_fields=['failure_reason'])
                payout.transition_to(Payout.Status.FAILED)
                logger.warning(
                    f"Payout {payout.id} marked as FAILED after {payout.attempt_count} attempts"
                )

                # Atomically refund held funds
                LedgerEntry.objects.create(
                    merchant=payout.merchant,
                    amount_paise=payout.amount_paise,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                    payout=payout,
                    description=f"Refund after max retries for payout {payout.id}"
                )
            else:
                # Reset to PENDING so process_payout can pick it up again
                payout.transition_to(Payout.Status.PENDING)

                # Exponential backoff delay: 30s, 60s, 120s
                delay = 30 * (2 ** payout.attempt_count)
                logger.info(
                    f"Payout {payout.id} reset to PENDING, retrying in {delay}s (attempt {payout.attempt_count})"
                )

                process_payout.apply_async(args=[str(payout.id)], countdown=delay)

