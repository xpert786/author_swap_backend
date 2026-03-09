import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import SubscriberGrowth, CampaignAnalytic, SubscriberVerification

User = get_user_model()
user = User.objects.get(username='ariyan') # Assuming 'ariyan' exists based on terminal prompt

# 1. Update Verification stats
verification, _ = SubscriberVerification.objects.get_or_create(user=user)
verification.audience_size = 0
verification.avg_open_rate = 0
verification.avg_click_rate = 0
verification.list_health_score = 0
verification.bounce_rate = 0
verification.unsubscribe_rate = 0
verification.active_rate = 0
verification.avg_engagement = 0
verification.is_connected_mailerlite = True
verification.save()

# 2. Seed Growth Data
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
counts = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

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
        "subscribers": 0,
        "open_rate": 0,
        "click_rate": 0,
        "type": "Recent"
    },
    {
        "name": "New Release: Coastal Hearts",
        "date": date(2023, 6, 8),
        "subscribers": 0,
        "open_rate": 0,
        "click_rate": 0,
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
