import os
import sys
import django
sys.path.append('/home/ariyan/Ariyan/author_swap_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from core.models import NewsletterSlot

User = get_user_model()
client = Client()

user = User.objects.first()
if not user:
    user = User.objects.create(username="testuser", email="test@example.com")

client.force_login(user)

slot = NewsletterSlot.objects.filter(user=user).first()
if not slot:
    slot = NewsletterSlot.objects.create(
        user=user, 
        send_date='2026-03-01', 
        send_time='12:00:00',
        audience_size=1000,
        preferred_genre='fantasy'
    )

print(f"Testing editing slot {slot.id}...")

print("Before Update GET:")
response = client.get(f'/authorswap/api/slots/{slot.id}/details/')
print(response.json())

print("\nPATCH request to edit slot...")
response = client.patch(
    f'/authorswap/api/slots/{slot.id}/details/', 
    {'preferred_genre': 'comics_graphic', 'visibility': 'friend_only'}, 
    content_type='application/json'
)
print("Status:", response.status_code)
print(response.json())

print("\nVerify update with GET:")
response = client.get(f'/authorswap/api/slots/{slot.id}/details/')
print(response.json())
