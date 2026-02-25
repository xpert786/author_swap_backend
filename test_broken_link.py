import requests
import json

def test_broken_link_request():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, let's update our book to have the "broken" link mentioned by the user
    update_book_url = "http://127.0.0.1:8000/authorswap/api/book/6/" # Using the book ID 6 from previous tests
    book_data = {
        "amazon_url": "http://blog.testsite.com/home" # This link used to cause failure
    }
    requests.patch(update_book_url, json=book_data, headers=headers)
    
    # Now try to send a swap request for slot 19
    detail_url = "http://127.0.0.1:8000/authorswap/api/swap-requests/19/"
    
    print(f"POST to {detail_url} (with broken link in book)...")
    
    # We need a new slot because the previous test already created a request for 19
    # Let's use a different ID or just ignore the duplication error for this test
    resp = requests.post(detail_url, json={}, headers=headers)
    
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=4))

if __name__ == "__main__":
    test_broken_link_request()
