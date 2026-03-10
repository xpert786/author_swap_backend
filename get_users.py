import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.contrib.auth import get_user_model
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()
for u in User.objects.all():
    email = u.email
    print(f"User ID {u.id}: {email}")
    if email:
        try:
            customers = stripe.Customer.list(email=email)
            for c in customers.data:
                subs = stripe.Subscription.list(customer=c.id, status='all')
                for s in subs.data:
                    print(f"  -> Stripe Customer {c.id} has Subscription {s.id} ({s.status})")
        except Exception as e:
            print(f"Stripe error for {email}: {e}")
