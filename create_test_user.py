import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.contrib.auth.models import User

# Create test user if doesn't exist
if not User.objects.filter(email='test@example.com').exists():
    user = User.objects.create_user('testuser', 'test@example.com', 'password123')
    print(f'User created: {user.email}')
else:
    user = User.objects.get(email='test@example.com')
    print(f'User already exists: {user.email}')
