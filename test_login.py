import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

import requests
import json

# Test the login endpoint
url = 'http://127.0.0.1:8000/api/login/'
data = {
    'email': 'test@example.com',
    'password': 'password123'
}

try:
    response = requests.post(url, json=data)
    print(f'Status Code: {response.status_code}')
    print(f'Response: {response.json()}')
except Exception as e:
    print(f'Error: {e}')
