import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

def clear_subs(email):
    print(f"Finding customers for {email}...")
    customers = stripe.Customer.list(email=email)
    deleted_count = 0
    for c in customers.data:
        subs = stripe.Subscription.list(customer=c.id, status='active')
        for sub in subs.data:
            stripe.Subscription.delete(sub.id)
            print(f"Deleted active subscription {sub.id} for customer {c.id}")
            deleted_count += 1
            
        subs = stripe.Subscription.list(customer=c.id, status='trialing')
        for sub in subs.data:
            stripe.Subscription.delete(sub.id)
            print(f"Deleted trialing subscription {sub.id} for customer {c.id}")
            deleted_count += 1
            
    print(f"Total subscriptions cancelled in Stripe: {deleted_count}")

# Assuming the user is testing with pinki@yopmail.com from the screenshot
clear_subs('pinki@yopmail.com')
