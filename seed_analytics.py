import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import SubscriberGrowth, CampaignAnalytic, SubscriberVerification

User = get_user_model()
user = User.objects.first()

if not user:
    user = User.objects.create_user(username='testadmin', email='admin@example.com', password='password123')
    print(f"Created user: {user.username}")

# 1. Update Verification stats
verification, _ = SubscriberVerification.objects.get_or_create(user=user)
verification.audience_size = 12457
verification.avg_open_rate = 42.3
verification.avg_click_rate = 8.7
verification.list_health_score = 87
verification.bounce_rate = 1.2
verification.unsubscribe_rate = 0.4
verification.active_rate = 94.0
verification.avg_engagement = 4.8
verification.is_connected_mailerlite = True
verification.save()

# 2. Seed Growth Data
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
counts = [1000, 1500, 1200, 2500, 3500, 1800, 2200, 5000, 4500, 6000, 11000, 12457]

for i, month in enumerate(months):
    SubscriberGrowth.objects.update_or_create(
        user=user,
        month=month,
        year=2024,
        defaults={'count': counts[i]}
    )

# 3. Seed Campaigns
campaigns = [
    {
        "name": "June Newsletter - Romance Special",
        "date": date(2023, 6, 15),
        "subscribers": 12457,
        "open_rate": 42.1,
        "click_rate": 8.7,
        "type": "Recent"
    },
    {
        "name": "New Release: Coastal Hearts",
        "date": date(2023, 6, 8),
        "subscribers": 12615,
        "open_rate": 42.1,
        "click_rate": 8.7,
        "type": "Recent"
    }
]

for camp_data in campaigns:
    CampaignAnalytic.objects.update_or_create(
        user=user,
        name=camp_data['name'],
        defaults=camp_data
    )

print("Successfully seeded Analytics data.")
