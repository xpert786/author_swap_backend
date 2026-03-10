import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from core.models import UserSubscription
from django.contrib.auth import get_user_model

User = get_user_model()
for sub in UserSubscription.objects.all():
    print(f"User: {sub.user.email}, Tier: {sub.tier.name}, Stripe Sub: {sub.stripe_subscription_id}")
