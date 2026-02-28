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
client.force_login(user)

slot = NewsletterSlot.objects.filter(user=user).first()

print(f"Testing export for slot {slot.id}...")

print("\n--- Google Calendar Export ---")
response = client.get(f'/authorswap/api/newsletter-slot/{slot.id}/export/?format=google')
print("Status:", response.status_code)
print(response.json())

print("\n--- Outlook Export ---")
response = client.get(f'/authorswap/api/newsletter-slot/{slot.id}/export/?format=outlook')
print("Status:", response.status_code)
print(response.json())

print("\n--- ICS Export ---")
response = client.get(f'/authorswap/api/newsletter-slot/{slot.id}/export/?format=ics')
print("Status:", response.status_code)
print(response.content[:200], "...") # Print first 200 chars
