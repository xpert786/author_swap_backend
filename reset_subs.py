import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from core.models import UserSubscription

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()

print("Checking all users and clearing active subscriptions in Stripe...")
deleted_stripe_count = 0
deleted_local_count = 0

for user in User.objects.all():
    email = user.email
    if not email:
        continue
        
    # Check Stripe for this email
    customers = stripe.Customer.list(email=email)
    for c in customers.data:
        # Get active subs
        subs = stripe.Subscription.list(customer=c.id, status='active')
        for sub in subs.data:
            stripe.Subscription.delete(sub.id)
            print(f"Cancelled ACTIVE Stripe sub {sub.id} for {email}")
            deleted_stripe_count += 1
            
        # Get trialing subs
        subs = stripe.Subscription.list(customer=c.id, status='trialing')
        for sub in subs.data:
            stripe.Subscription.delete(sub.id)
            print(f"Cancelled TRIALING Stripe sub {sub.id} for {email}")
            deleted_stripe_count += 1
            
    # Also wipe out the local DB subscription if it exists, so they start fresh
    local_subs = UserSubscription.objects.filter(user=user)
    if local_subs.exists():
        count, _ = local_subs.delete()
        deleted_local_count += count
        print(f"Deleted local UserSubscription for {email}")

print(f"\nDone. Cancelled {deleted_stripe_count} Stripe subs, deleted {deleted_local_count} local subs.")
