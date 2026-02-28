import os
import sys
import django
sys.path.append('/home/ariyan/Ariyan/author_swap_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from core.models import SubscriptionTier, UserSubscription

User = get_user_model()
client = Client()

user = User.objects.first()
if not user:
    user = User.objects.create(username="testuser", email="test@example.com")

tier = SubscriptionTier.objects.first()

client.force_login(user)

print("GET request before POST...")
response = client.get('/authorswap/api/subscriber-verification/')
print(response.json())

if tier:
    print("\nPOST request...")
    response = client.post('/authorswap/api/subscriber-verification/', {'tier_id': tier.id}, content_type='application/json')
    print(response.json())

print("\nGET request after POST...")
response = client.get('/authorswap/api/subscriber-verification/')
print(response.json())
