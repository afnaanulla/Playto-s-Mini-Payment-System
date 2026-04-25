from django.urls import path
from .views import PayoutCreateView, MerchantBalanceView, MerchantPayoutListView, MerchantListView, HealthCheckView, LedgerView

urlpatterns = [
    path('v1/merchants', MerchantListView.as_view(), name='merchant-list'),
    path('v1/payouts', PayoutCreateView.as_view(), name='payout-create'),
    path('v1/merchants/<uuid:merchant_id>/balance', MerchantBalanceView.as_view(), name='merchant-balance'),
    path('v1/merchants/<uuid:merchant_id>/payouts', MerchantPayoutListView.as_view(), name='merchant-payouts'),
    path('v1/merchants/<uuid:merchant_id>/ledger', LedgerView.as_view(), name='merchant-ledger'),
    path('v1/health', HealthCheckView.as_view(), name='health-check'),
]
