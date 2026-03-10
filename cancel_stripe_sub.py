import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

import stripe
from django.conf import settings
from core.models import UserSubscription

stripe.api_key = settings.STRIPE_SECRET_KEY.strip()

# Target: customer + subscription from the API response
STRIPE_CUSTOMER_ID = "cus_U7d1necXNweC7f"
STRIPE_SUBSCRIPTION_ID = "sub_1T9NleEIxKwaOjPAxSa3H60V"

print(f"Cancelling Stripe subscription: {STRIPE_SUBSCRIPTION_ID} ...")
try:
    result = stripe.Subscription.delete(STRIPE_SUBSCRIPTION_ID)
    print(f"Result status: {result.status}")
except stripe.error.InvalidRequestError as e:
    print(f"Stripe error (maybe already cancelled): {e}")

print(f"Clearing customer balance for: {STRIPE_CUSTOMER_ID} ...")
try:
    stripe.Customer.modify(STRIPE_CUSTOMER_ID, balance=0)
    print("Balance cleared.")
except Exception as e:
    print(f"Balance clear error: {e}")

print("Deleting local UserSubscription records for this customer ...")
deleted_count, _ = UserSubscription.objects.filter(
    stripe_customer_id=STRIPE_CUSTOMER_ID
).delete()
print(f"Deleted {deleted_count} local subscription record(s).")

print("\nAll done. The user should now see no subscription.")
