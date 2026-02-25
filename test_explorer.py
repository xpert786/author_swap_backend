import requests
import json

def test_explorer():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return

    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    explore_url = "http://127.0.0.1:8000/authorswap/api/slots/explore/"
    print(f"Fetching {explore_url}...")
    
    resp = requests.get(explore_url, headers=headers)
    if resp.status_code == 200:
        print("Success! Data received:")
        data = resp.json()
        print(json.dumps(data[:1], indent=4))
    else:
        print(f"Failed with status {resp.status_code}:")
        print(resp.text)

if __name__ == "__main__":
    test_explorer()
