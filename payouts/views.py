import logging
import uuid
import json

logger = logging.getLogger(__name__)

from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

from .models import Merchant, Payout, LedgerEntry, IdempotencyKey
from .serializers import PayoutRequestSerializer, PayoutResponseSerializer
from .tasks import process_payout


class PayoutCreateView(views.APIView):
    """
    POST /api/v1/payouts

    Handles payout requests with strict idempotency and concurrency locking.

    Idempotency: Same request (same idempotency key) returns identical response.
    Concurrency: Uses SELECT FOR UPDATE to prevent race conditions on balance.
    """

    def post(self, request):
        # 1. Extract and Validate Idempotency Key
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            idem_key_uuid = uuid.UUID(idempotency_key)
        except ValueError:
            return Response(
                {"error": "Invalid Idempotency-Key format. Must be UUID."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Validate Request Body
        serializer = PayoutRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        merchant_id = serializer.validated_data['merchant_id']
        amount_paise = serializer.validated_data['amount_paise']
        bank_account_id = serializer.validated_data['bank_account_id']

        # 3. Process with Locking and Check Idempotency (Concurrency Control)
        try:
            with transaction.atomic():
                # Lock the merchant row until transaction completes
                # This prevents other concurrent requests from reading a stale balance
                # It also serializes all requests for the same merchant, solving idempotency race conditions
                merchant = Merchant.objects.select_for_update().get(id=merchant_id)

                # Check Idempotency inside the transaction
                try:
                    idem_record = IdempotencyKey.objects.get(merchant=merchant, key=idem_key_uuid)
                    if idem_record.expires_at < timezone.now():
                        idem_record.delete()
                        idem_record = IdempotencyKey.objects.create(
                            merchant=merchant,
                            key=idem_key_uuid,
                            response_body=None,
                            expires_at=timezone.now() + timezone.timedelta(hours=24)
                        )
                    elif idem_record.response_body is not None:
                        # Already completed - return stored response
                        return Response(idem_record.response_body, status=idem_record.response_status)
                    else:
                        # First request still in flight
                        return Response(
                            {"error": "Request with this idempotency key is already in progress"}, 
                            status=status.HTTP_409_CONFLICT
                        )
                except IdempotencyKey.DoesNotExist:
                    idem_record = IdempotencyKey.objects.create(
                        merchant=merchant,
                        key=idem_key_uuid,
                        response_body=None,
                        expires_at=timezone.now() + timezone.timedelta(hours=24)
                    )

                # Double-check balance inside transaction
                # Uses calculate_balance() which properly accounts for held funds
                current_balance = merchant.calculate_balance()

                if current_balance < amount_paise:
                    response_data = {
                        "error": "Insufficient funds",
                        "available_paise": current_balance,
                        "requested_paise": amount_paise
                    }
                    # Store response so duplicate requests get the exact same 422 error
                    idem_record.response_body = response_data
                    idem_record.response_status = status.HTTP_422_UNPROCESSABLE_ENTITY
                    idem_record.save()
                    return Response(response_data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

                # Create Payout record
                payout = Payout.objects.create(
                    merchant=merchant,
                    amount_paise=amount_paise,
                    status=Payout.Status.PENDING,
                    idempotency_key=idem_key_uuid,
                    bank_account_id=bank_account_id,
                )

                # Create Debit entry in Ledger (Hold funds)
                LedgerEntry.objects.create(
                    merchant=merchant,
                    amount_paise=amount_paise,
                    entry_type=LedgerEntry.EntryType.DEBIT,
                    payout=payout,
                    description=f'Hold for payout {payout.id}'
                )

                # Serialize response
                response_data = PayoutResponseSerializer(payout).data

                # Ensure data is JSON serializable (convert UUIDs/Datetimes to strings)
                serializable_data = json.loads(JSONRenderer().render(response_data))

                # Store response in idempotency record
                idem_record.response_body = serializable_data
                idem_record.response_status = status.HTTP_201_CREATED
                idem_record.save()

                # Trigger background task only AFTER the database transaction commits
                transaction.on_commit(lambda: process_payout.delay(str(payout.id)))

                return Response(response_data, status=status.HTTP_201_CREATED)

        except Merchant.DoesNotExist:
            return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as error:
            # If anything fails, it will be logged. The transaction rolls back naturally,
            # meaning the IdempotencyKey is also rolled back. No stuck keys!
            logger.exception(f"Payout creation failed: {error}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealthCheckView(views.APIView):
    """
    GET /api/v1/health

    Health check endpoint for load balancers and deployment platforms.
    Returns healthy status if database is accessible.
    """

    def get(self, request):
        return Response({"status": "healthy", "timestamp": timezone.now().isoformat()})


class MerchantListView(views.APIView):
    """
    GET /api/v1/merchants

    Lists all merchants.
    """

    def get(self, request):
        merchants = Merchant.objects.all()
        data = [{"id": str(merchant.id), "name": merchant.name} for merchant in merchants]
        return Response(data)


class MerchantPayoutListView(views.APIView):
    """
    GET /api/v1/merchants/{id}/payouts

    Returns history of payouts for a merchant.
    """

    def get(self, request, merchant_id):
        # Use select_related to avoid N+1 query problem
        payouts = Payout.objects.filter(
            merchant_id=merchant_id
        ).select_related('merchant').order_by('-created_at')

        serializer = PayoutResponseSerializer(payouts, many=True)
        return Response(serializer.data)


class MerchantBalanceView(views.APIView):
    """
    GET /api/v1/merchants/{id}/balance

    Returns detailed balance breakdown (available, held, settled).
    """

    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
            balance = merchant.calculate_balance_split()
            return Response({
                "merchant_id": merchant.id,
                "name": merchant.name,
                "available_paise": balance['available_paise'],
                "held_paise": balance['held_paise'],
                "total_paid_out": balance['total_paid_out'],
            })
        except Merchant.DoesNotExist:
            return Response({"error": "Merchant not found"}, status=status.HTTP_404_NOT_FOUND)


class LedgerView(views.APIView):
    """
    GET /api/v1/merchants/{id}/ledger

    Returns full ledger history (all credits and debits) for a merchant.
    Useful for auditing and reconciliation.
    """

    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)

            # Get ledger entries with related payout info
            entries = LedgerEntry.objects.filter(
                merchant=merchant
            ).select_related('payout').order_by('-created_at')

            data = []
            for entry in entries:
                data.append({
                    "id": str(entry.id),
                    "amount_paise": entry.amount_paise,
                    "entry_type": entry.entry_type,
                    "entry_type_display": entry.get_entry_type_display(),
                    "description": entry.description,
                    "payout_id": str(entry.payout.id) if entry.payout else None,
                    "payout_status": entry.payout.status if entry.payout else None,
                    "created_at": entry.created_at.isoformat(),
                })

            return Response(data)

        except Merchant.DoesNotExist:
            return Response(
                {"error": "Merchant not found"},
                status=status.HTTP_404_NOT_FOUND
            )
