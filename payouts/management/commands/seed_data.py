from django.core.management.base import BaseCommand
from payouts.models import Merchant, LedgerEntry
import uuid

class Command(BaseCommand):
    help = 'Seeds initial merchant and ledger data'

    def handle(self, *args, **kwargs):
        # Clear existing data
        LedgerEntry.objects.all().delete()
        Merchant.objects.all().delete()

        merchants_data = [
            {"name": "Aman Agencies", "bank": "HDFC000123"},
            {"name": "Priya Freelancing", "bank": "ICIC000456"},
            {"name": "Global Tech Solns", "bank": "SBIN000789"},
        ]

        for data in merchants_data:
            merchant = Merchant.objects.create(
                name=data['name'],
                bank_account_id=data['bank']
            )
            
            # Seed 3 credit entries for each merchant (Total ~10,000 INR = 1,000,000 Paise)
            amounts = [200000, 300000, 500000] # in paise
            for amount in amounts:
                LedgerEntry.objects.create(
                    merchant=merchant,
                    amount_paise=amount,
                    entry_type=LedgerEntry.EntryType.CREDIT
                )
            
            balance = merchant.calculate_balance()
            self.stdout.write(
                self.style.SUCCESS(f'Created {merchant.name} with balance: {balance} paise')
            )
