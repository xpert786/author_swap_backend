import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from core.views import NewsletterSlotExportView
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from core.models import NewsletterSlot

def test():
    User = get_user_model()
    user = User.objects.first()
    slot = NewsletterSlot.objects.filter(user=user).last()
    if not slot:
        print("No slot found")
        return
    print(f"Testing with User: {user.username} (ID: {user.id}), Slot ID: {slot.id} (Owner ID: {slot.user.id})")

    factory = APIRequestFactory()
    view = NewsletterSlotExportView()
    view.format_kwarg = None
    view.kwargs = {'pk': slot.id}

    # Test ICS
    request = factory.get('/?format=ics')
    force_authenticate(request, user=user)
    drf_request = view.initialize_request(request)
    view.request = drf_request
    response = view.get(drf_request, pk=slot.id)
    print(f"ICS Status: {response.status_code}")
    if response.status_code == 200:
        print("ICS Content Sample:")
        print(response.content.decode()[:200])

    # Test Google
    request = factory.get('/?format=google')
    force_authenticate(request, user=user)
    drf_request = view.initialize_request(request)
    view.request = drf_request
    response = view.get(drf_request, pk=slot.id)
    print(f"Google Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Google URL: {response.data.get('url')}")

    # Test Outlook
    request = factory.get('/?format=outlook')
    force_authenticate(request, user=user)
    drf_request = view.initialize_request(request)
    view.request = drf_request
    response = view.get(drf_request, pk=slot.id)
    print(f"Outlook Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Outlook URL: {response.data.get('url')}")


if __name__ == "__main__":
    test()
