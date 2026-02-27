import requests
import json

def test_request():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try sending request with just 'slot_id' in body
    request_url = "http://127.0.0.1:8000/authorswap/api/swap-requests/"
    data = {"slot_id": 14} # We know slot 14 exists from previous test
    
    print(f"Sending request to {request_url} with data: {data}")
    resp = requests.post(request_url, json=data, headers=headers)
    
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

    # Try sending request via the new URL with ID in path
    url_id = "http://127.0.0.1:8000/authorswap/api/slots/15/request/"
    print(f"\nSending request to {url_id} (empty body)...")
    resp = requests.post(url_id, json={}, headers=headers)
    
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")

if __name__ == "__main__":
    test_request()
