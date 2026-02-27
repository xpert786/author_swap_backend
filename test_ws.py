import asyncio
import websockets
import json
import requests
import sys

async def test_notification():
    # Login to get token
    login_url = "http://127.0.0.1:8000/authorswap/api/login/"
    creds = {"email": "admin@gmail.com", "password": "admin"}
    print(f"Logging in at {login_url}...")
    
    resp = requests.post(login_url, json=creds)
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return

    tokens = resp.json()
    access_token = tokens['access']
    print("Login successful.")

    # WebSocket URL
    ws_url = f"ws://127.0.0.1:8000/authorswap/ws/notification/?token={access_token}"
    print(f"Connecting to WebSocket at {ws_url}...")

    try:
        async with websockets.connect(ws_url) as websocket:
            print("WebSocket connected.")

            # Trigger a notification via API
            test_noti_url = "http://127.0.0.1:8000/authorswap/api/test-notification/"
            headers = {"Authorization": f"Bearer {access_token}"}
            print(f"Triggering notification at {test_noti_url}...")
            
            requests.post(test_noti_url, headers=headers)
            
            # Wait for the notification message
            print("Waiting for message from WebSocket...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(message)
                print("Received notification message:")
                print(json.dumps(data, indent=4))
            except asyncio.TimeoutError:
                print("Timeout: No message received after 10 seconds.")
                
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_notification())
