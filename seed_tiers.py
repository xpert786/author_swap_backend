import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from core.models import SubscriptionTier

tiers = [
    {
        "name": "Tier 1",
        "price": 9.99,
        "label": "Swap Only",
        "features": [
            "Unlimited Newsletter swaps",
            "No paid placements",
            "Automatic send confirmation",
            "Email support (typical response within 2 business days)"
        ],
        "best_for": "Authors growing their audience or promoting their books through swaps only."
    },
    {
        "name": "Tier 2",
        "price": 28.99,
        "label": "Starter",
        "is_most_popular": True,
        "features": [
            "Unlimited newsletter swaps",
            "Up to 10 paid placements/month",
            "Automatic send verification",
            "Priority email support (typical response within 1 business day)",
            "No commissions — authors keep 100% of placement revenue"
        ],
        "best_for": "Authors selling a few paid slots per week."
    },
    {
        "name": "Tier 3",
        "price": 48.99,
        "label": "Growth",
        "features": [
            "Unlimited newsletter swaps",
            "Up to 30 paid placements/month",
            "Automatic send verification",
            "High-priority email support (faster responses during business hours)",
            "No commissions — authors keep 100% of placement revenue"
        ],
        "best_for": "Authors monetizing their newsletters regularly."
    },
    {
        "name": "Tier 4",
        "price": 78.99,
        "label": "Professional",
        "features": [
            "Unlimited newsletter swaps",
            "Unlimited placements",
            "Automatic send verification",
            "Top-priority support (fastest response, issue escalation when needed)",
            "No commissions — authors keep 100% of placement revenue"
        ],
        "best_for": "Authors selling paid placements daily or near-daily."
    }
]

for tier_data in tiers:
    SubscriptionTier.objects.update_or_create(
        name=tier_data['name'],
        defaults=tier_data
    )

print("Successfully seeded Subscription Tiers.")
