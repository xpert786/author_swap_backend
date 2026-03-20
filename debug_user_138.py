import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import SubscriberVerification, UserSubscription
User = get_user_model()

try:
    user = User.objects.get(id=138)
    print(f"User 138: {user.email}")
    
    verification = getattr(user, 'verification', None)
    if verification:
        print(f"Verification ID: {verification.id}, connected: {verification.is_connected_mailerlite}")
        print(f"Verification created_at: {verification.id}") # No created_at in model, using ID as proxy
    else:
        print("No verification found for user 138")
        
    subscription = getattr(user, 'subscription', None)
    if subscription:
        print(f"Subscription ID: {subscription.id}, tier: {subscription.tier}, stripe_id: {subscription.stripe_subscription_id}")
    else:
        print("No subscription found for user 138")

except User.DoesNotExist:
    print("User 138 does not exist in DB")
