#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.contrib.auth import get_user_model, authenticate

User = get_user_model()

# Test with hardcoded credentials for debugging
email = input("Enter email: ")
password = input("Enter password: ")

print(f"\n--- Debugging Login for: {email} ---\n")

# 1. Check if user exists
try:
    user = User.objects.get(email=email)
    print(f"✓ User found: {user.username} (ID: {user.id})")
    print(f"  Email: {user.email}")
    print(f"  Is active: {user.is_active}")
    print(f"  Is staff: {user.is_staff}")
    print(f"  Is superuser: {user.is_superuser}")
    
    # 2. Check password
    password_valid = user.check_password(password)
    print(f"\n✓ Password check: {'VALID' if password_valid else 'INVALID'}")
    
    # 3. Try authenticate with email as username
    auth_user = authenticate(username=email, password=password)
    print(f"\n✓ Authenticate with email as username: {auth_user}")
    
    # 4. Try authenticate with username
    auth_user2 = authenticate(username=user.username, password=password)
    print(f"✓ Authenticate with username '{user.username}': {auth_user2}")
    
except User.DoesNotExist:
    print(f"✗ No user found with email: {email}")
    print("\nAvailable users:")
    for u in User.objects.all()[:5]:
        print(f"  - {u.email} (username: {u.username})")

except Exception as e:
    print(f"✗ Error: {e}")
