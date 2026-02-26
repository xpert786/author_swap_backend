# AuthorSwap: MailerLite Integration Guide

This guide explains how the backend integrates with MailerLite for audience verification and swap notifications.

## Overview
AuthorSwap uses MailerLite for two main purposes:
1.  **Audience Verification**: Confirming the actual subscriber count of an author.
2.  **Swap Notifications**: Moving subscribers between specific MailerLite Groups to trigger automated emails (Pending, Approved, Rejected).

---

## 1. Connecting MailerLite
Authors provide their API Key in the settings page to establish a connection.

*   **Endpoint**: `POST /api/connect-mailerlite/`
*   **Payload**:
    ```json
    {
      "api_key": "ml_api_xxxxxxxxxxxxxxxx"
    }
    ```
*   **Backend Logic**: 
    1.  Validates the key with MailerLite.
    2.  Fetches the total subscriber count.
    3.  Updates the author's `Profile` and `SubscriberVerification` models.
    4.  Updates all the author's public `NewsletterSlot`s with the verified audience size.

---

## 2. Syncing Analytics
Used to pull real-time open rates, click rates, and recent campaign data.

*   **Endpoint**: `GET /api/subscriber-analytics/`
*   **Response Payload**:
    ```json
    {
      "summary_stats": {
        "active_subscribers": 12450,
        "avg_open_rate": "42.5%",
        "avg_click_rate": "8.2%",
        "list_health_score": "95/100"
      },
      "growth_chart": [...],
      "campaign_analytics": [...]
    }
    ```
*   **Backend Logic**: Hits the MailerLite `/campaigns` and `/stats` endpoints to update the author's local analytics records.

---

## 3. Swap Life Cycle & Groups
The backend automatically moves authors into different MailerLite groups based on the status of their swap requests. You should create these groups in your MailerLite dashboard and set their IDs in the backend `settings.py`.

### A. New Swap Request (Sent)
*   **Triggers**: When `POST /api/slots/<id>/request/` is called.
*   **MailerLite Action**: Adds the **Receiving Author** to the `PENDING` group.
*   **Usage**: You can set up a MailerLite "Automation" to send an email saying "You have a new swap request!" whenever someone enters this group.

### B. Accepting a Swap
*   **Triggers**: When `POST /api/accept-swap/<id>/` is called.
*   **MailerLite Action**: 
    1.  Removes the author from the `PENDING` group.
    2.  Adds the author to the `APPROVED` group.
*   **Usage**: Triggers an automated email saying "Your swap was accepted! Here's what to do next."

### C. Declining a Swap
*   **Triggers**: When `POST /api/reject-swap/<id>/` is called.
*   **MailerLite Action**:
    1.  Removes the author from the `PENDING` group.
    2.  Adds the author to the `REJECTED` group.

---

## Technical Configuration
The following settings must be configured in `author_swap/settings.py` or as environment variables:

```python
MAILERLITE_API_KEY = "..."
MAILERLITE_PENDING_GROUP_ID = "..."
MAILERLITE_APPROVED_GROUP_ID = "..."
MAILERLITE_REJECTED_GROUP_ID = "..."
```

*Note: The platform remains operational even if MailerLite is disconnected or the API is down, as it uses local database records for all critical UI displays.*
