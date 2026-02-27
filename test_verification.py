import requests
import json

def test_verification():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    url = "http://127.0.0.1:8000/authorswap/api/subscriber-verification/"
    print(f"Fetching {url}...")
    resp = requests.get(url, headers=headers)
    
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=4))

if __name__ == "__main__":
    test_verification()
