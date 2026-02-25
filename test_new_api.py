import requests
import json
import sqlite3

def test_new_api():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    # Delete previous requests to slot 19 so we can request it again with full fields
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    c.execute("DELETE FROM core_swaprequest WHERE slot_id = 19")
    conn.commit()
    conn.close()

    # New dedicated API exactly matching user parameters
    api_url = "http://127.0.0.1:8000/authorswap/api/slots/19/request-placement/"
    
    # Simulating the UI form from the image "Request Swap Placement"
    payload = {
        "book": 6,                                    # The book picked from "Choose a Book to Promote"
        "preferred_placement": "top",                 # Radio buttons: "Top", "Middle", "Bottom"
        "max_partners_acknowledged": 5,               # Dropdown: "Max Partners Allowed"
        "amazon_url": "https://amazon.com/dp/NEWAPI", # Retailer Links section
        "apple_url": "https://apple.com/book/api",
        "kobo_url": "",
        "barnes_noble_url": "",
        "message": "Write your message to author here!"
    }
    
    print(f"POST to {api_url} ...")
    resp = requests.post(api_url, json=payload, headers=headers)
    
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=4))

if __name__ == "__main__":
    test_new_api()
