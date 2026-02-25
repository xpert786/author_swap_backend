import requests
import json

def test_detail_post():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    # We'll use slot 19 if it exists, or create/find another one
    # Note: Previous tests used 14 and 15
    detail_url = "http://127.0.0.1:8000/authorswap/api/swap-requests/19/"
    
    print(f"POST to {detail_url} (should create swap request for slot 19)...")
    # Empty body to trigger auto-book selection
    resp = requests.post(detail_url, json={}, headers=headers)
    
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

if __name__ == "__main__":
    test_detail_post()
