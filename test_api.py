import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from core.views import SubscriberVerificationView

User = get_user_model()
factory = RequestFactory()
view = SubscriberVerificationView.as_view()

for u in User.objects.all():
    request = factory.get('/api/subscriber-verification/')
    request.user = u
    try:
        response = view(request)
        print(f"User {u.email}: subscription data is = {response.data.get('subscription')}")
    except Exception as e:
        print(f"Error for {u.email}: {e}")
