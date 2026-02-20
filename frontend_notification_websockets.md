# Frontend Notification WebSockets Integration Guide

## Overview
We've implemented a WebSocket-based real-time notification system using Django Channels. This enables users to receive isolated, user-friendly notifications the moment a related event (like a new Swap Request) occurs, without having to refresh the page or poll an API.

## Connection Details
- **Endpoint:** `ws://<your-backend-domain>/ws/notifications/`
- **Authentication:** The WebSocket connection requires the user to be authenticated. You must pass the user's JWT Access Token as a query parameter when establishing the connection.
  - **Example URL formulation:** `ws://127.0.0.1:8000/ws/notifications/?token=YOUR_JWT_ACCESS_TOKEN`

## Expected Behavior
- **Isolation:** Each user is automatically assigned to their own isolated WebSocket group. This group is determined securely via the user ID encoded in the provided JWT token. They will only receive notifications specifically intended for them.
- **Data Structure:** When a notification is broadcasted, the WebSocket will push a stringified JSON payload containing the new notification data. Re-parsing the payload typically yields:
  ```json
  {
      "type": "notification",
      "data": {
          "id": 12,
          "title": "New Swap Request 🎉",
          "badge": "SWAP",
          "message": "Great news! AuthorName has requested a swap for your Fantasy newsletter slot scheduled on 2024-05-15.",
          "action_url": "/dashboard/swaps/45/",
          "is_read": false,
          "created_at": "2024-04-10T14:32:00Z"
      }
  }
  ```

## Friendly Sentences
The backend has been updated to generate human-readable, friendly notification messages out-of-the-box. Instead of assembling data on the frontend or reading raw logs, the backend pushes pre-formatted text (e.g., `"Great news! UserX has requested a swap..."`). The frontend only needs to render the `message` and `title` fields directly into the UI components.

## Implementation Instructions for Frontend (No Code)
1. **Connect on Login:** Initialize a WebSocket connection to the endpoint as soon as the user logs in and a valid JWT access token is available. If using an in-memory/global state for the token, ensure the socket is spun up then.
2. **Handle Messages:** Add an event listener to the WebSocket to listen for incoming messages. Whenever a message is received, parse the JSON payload.
3. **Update UI:** Intercept payloads where `type` is `"notification"`. Extract the nested `data` object and use it to trigger a Toast notification, increment a notification bell counter, or place it at the top of a dropdown list of notifications.
4. **Cleanup:** Remember to close the WebSocket connection gracefully when the user logs out or the token expires.
