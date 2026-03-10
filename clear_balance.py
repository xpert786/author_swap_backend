import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

print("Clearing all customer balances...")
for u in User.objects.all():
    if u.email:
        customers = stripe.Customer.list(email=u.email)
        for c in customers.data:
            if c.balance != 0:
                print(f"Clearing balance for {u.email} (Customer {c.id}) - was {c.balance}")
                stripe.Customer.modify(c.id, balance=0)
print("Done.")
