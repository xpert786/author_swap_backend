# AuthorSwap Swap Process Flow

Based on the Figma designs and the backend implementation, the entire "handshake" process of discovering swap partners, sending requests, and accepting those requests happens **entirely within the AuthorSwap platform**. Email service providers (like MailerLite) are only used *later* for the actual act of sending the newsletter to subscribers.

Here is a step-by-step breakdown of how the APIs work to facilitate this:

---

## 1. Finding Swap Partners (Figma Screen: Swap Partner)
Authors browse a directory of available newsletter slots that other authors have published.

*   **API Endpoint:** `GET /api/slots/explore/`
*   **What it does:** This endpoint (`SlotExploreView`) queries the `NewsletterSlot` database table. It returns all slots that are marked as `public` and `available`, excluding the current user's own slots.
*   **Frontend Action:** The frontend displays these as cards. The user can use filter dropdowns (Genre, Audience Size, etc.) which append query parameters (e.g., `?genre=Fantasy`) to the API call.

---

## 2. Sending a Swap Request (Initiating the "Two-Way" Swap)
When an author clicks "Send Request" on another author's slot, a modal appears where they construct the proposed arrangement. According to the Figma ("Swap Arrangement" modal), an author offers one of their own slots in exchange.

*   **API Endpoint:** `POST /api/slots/<slot_id>/request/`
*   **What it does:** This endpoint (`SwapRequestListView.post`) creates a new row in the `SwapRequest` database table.
*   **The Payload:** The frontend sends a JSON payload representing both sides of the deal:
    ```json
    {
      "slot": 45,                  // The ID of the slot they want (Jane's Friday, May 17 slot)
      "requested_book": 12,        // The book John wants Jane to promote

      "offered_slot": 62,          // The ID of the slot the requester is offering (John's Wed, May 15 slot)
      "book": 8,                   // The book John is promising to promote for Jane

      "message": "Love your books! Would love to swap." // Optional personal message
    }
    ```
*   **Result:** A new `SwapRequest` is created with a status of **`pending`**. A notification is generated in the database for the slot owner.

---

## 3. Managing and Accepting Requests (Figma Screen: Swap Management)
The receiving author (Jane) navigates to their Swap Management dashboard to see incoming requests.

**Fetching the Dashboard:**
*   **API Endpoint:** `GET /api/swaps/?tab=pending`
*   **What it does:** The `SwapManagementListView` queries for `SwapRequest`s where the current user is either the requester or the slot owner. Because of `tab=pending`, it filters only `pending` requests.
*   **Result:** The UI renders the pending cards.

**Accepting the Request:**
*   **API Endpoint:** `POST /api/accept-swap/<request_id>/`
*   **What it does:** When Jane clicks "Accept", this endpoint (`AcceptSwapView`) verifies the request exists and is in the `pending` state.
*   **The Status Change:** It changes the `SwapRequest.status` from `pending` to **`confirmed`**.
*   **Result:** Because the status is now `confirmed`, the swap will disappear from the "Pending Swaps" tab and reappear in the "Scheduled Swaps" tab (as configured in the backend `TAB_STATUS_MAP`).

---

## Summary of the "Handshake"
1.  **John** triggers `GET /api/slots/explore/` -> finds Jane's slot.
2.  **John** triggers `POST /api/slots/45/request/` (payload includes John's offered slot & book + Jane's requested slot & book). Status is **`pending`**.
3.  **Jane** triggers `GET /api/swaps/?tab=pending` -> sees John's request.
4.  **Jane** triggers `POST /api/accept-swap/99/` -> Status changes to **`confirmed`**. The handshake is complete.

*Note: The platform tracks this agreement. On the actual dates (e.g., May 15 and May 17), it is up to the authors to actually configure their newsletters in MailerLite to send the agreed-upon books to their audiences.*
