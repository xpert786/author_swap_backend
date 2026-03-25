import requests

def test_add_book():
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    
    print("Logging in...")
    resp = requests.post(login_url, json=creds)
    token = resp.json()['access']
    headers = {"Authorization": f"Bearer {token}"}
    
    url = "http://127.0.0.1:8000/authorswap/api/add-book/"
    data = {
        "title": "Test Book",
        "primary_genre": "romance",
        "subgenres": ["contemporary"],
        "price_tier": "free",
        "amazon_url": "https://amazon.com",
        "apple_url": "https://apple.com",
        "kobo_url": "https://kobo.com",
        "barnes_noble_url": "https://bn.com",
        "availability": "all",
        "publish_date": "2024-01-01",
        "description": "Test description"
    }
    import io
    dummy_image = io.BytesIO(b"dummy image data")
    dummy_image.name = "test.jpg"
    files = {"book_cover": ("test.jpg", dummy_image, "image/jpeg")}
    print("Adding book with image...")
    resp = requests.post(url, data=data, files=files, headers=headers)
    print(resp.status_code, resp.text)

if __name__ == "__main__":
    test_add_book()
