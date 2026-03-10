import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

print("Checking customer balances...")
count = 0
for c in stripe.Customer.list(limit=100).data:
    if c.balance != 0:
        stripe.Customer.modify(c.id, balance=0)
        print(f"Cleared balance {c.balance} for Customer {c.id} ({c.email})")
        count += 1
print(f"Done. Cleared {count} balances.")
