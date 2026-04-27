from rest_framework import serializers
from .models import Payout, Merchant

class PayoutRequestSerializer(serializers.Serializer):
    merchant_id = serializers.UUIDField()
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=100)

class PayoutResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = ['id', 'merchant', 'amount_paise', 'status', 'bank_account_id', 'idempotency_key', 'created_at']
