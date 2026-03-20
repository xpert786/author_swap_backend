import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.contrib.auth.models import User
from authentication.views import get_onboarding_status

# Clean up if exists
User.objects.filter(email='newuser_test@example.com').delete()

# Create a new user
user = User.objects.create_user(username='newuser_test', email='newuser_test@example.com', password='password123')

# Profile should be created by signal
print(f"Profile exists: {hasattr(user, 'profile')}")
if hasattr(user, 'profile'):
    print(f"onboarding_completed: {user.profile.onboarding_completed}")
    print(f"pen_name: {user.profile.pen_name}")
    print(f"primary_genre: {user.profile.primary_genre}")

onboarding = get_onboarding_status(user)
print(f"Onboarding status: {onboarding}")
print(f"isprofilecompleted: {onboarding['all_complete']}")

# Clean up
user.delete()
