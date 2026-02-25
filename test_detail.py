import requests
import json

def test_detail():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    request_url = "http://127.0.0.1:8000/authorswap/api/swap-requests/23/"
    print(f"Fetching {request_url}...")
    resp = requests.get(request_url, headers=headers)
    
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success! Data received.")
    else:
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    test_detail()
