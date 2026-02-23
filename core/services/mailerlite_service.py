"""
MailerLite integration service for Author Swap.

Handles:
  A. Syncing audience size from MailerLite subscriber data
  B. Moving subscribers between groups on swap request/accept/reject
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# MailerLite SDK uses requests internally, so we wrap it safely
try:
    from mailerlite import MailerLiteApi
    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False


def _get_client():
    """
    Returns a configured MailerLite API client.
    Returns None if the SDK is unavailable or no API key is configured.
    """
    api_key = getattr(settings, 'MAILERLITE_API_KEY', None)
    if not api_key or not _HAS_SDK:
        logger.warning("MailerLite SDK not available or MAILERLITE_API_KEY not set.")
        return None
    return MailerLiteApi(api_key)


# ---------------------------------------------------------------------------
# A.  Audience Size Sync
# ---------------------------------------------------------------------------

def get_audience_size(email: str) -> int:
    """
    Fetches the audience/subscriber count associated with *email* from
    MailerLite.  Falls back to 0 when the service is unreachable.
    """
    client = _get_client()
    if client is None:
        return 0
    try:
        subscriber = client.subscribers.get(email)
        data = subscriber or {}
        # MailerLite stores custom fields; we look for 'audience_size' or use
        # the subscriber count of the groups they belong to.
        fields = data.get('fields', {})
        return int(fields.get('audience_size', 0))
    except Exception as e:
        logger.error(f"MailerLite get_audience_size failed for {email}: {e}")
        return 0


def sync_profile_audience(profile) -> int:
    """
    Convenience wrapper: given a Profile model instance, pull the latest
    audience size from MailerLite and persist it on the related
    NewsletterSlot(s).
    """
    email = profile.email or profile.user.email
    audience = get_audience_size(email)
    if audience > 0:
        # Update all public slots belonging to this user
        from core.models import NewsletterSlot
        NewsletterSlot.objects.filter(
            user=profile.user, visibility='public'
        ).update(audience_size=audience)
    return audience


# ---------------------------------------------------------------------------
# B.  Group Management  (Pending / Approved / Rejected)
# ---------------------------------------------------------------------------

def _group_id(name: str) -> str:
    """
    Reads MailerLite group IDs from Django settings.
    Expected settings keys:
        MAILERLITE_PENDING_GROUP_ID
        MAILERLITE_APPROVED_GROUP_ID
        MAILERLITE_REJECTED_GROUP_ID
    """
    key = f"MAILERLITE_{name.upper()}_GROUP_ID"
    return getattr(settings, key, '')


def send_swap_request_notification(author_email: str):
    """
    Called when a swap request is *created*.
    Adds the author to the "Pending Swaps" group so MailerLite can
    trigger an automated invitation/notification email.
    """
    client = _get_client()
    group_id = _group_id('PENDING')
    if client is None or not group_id:
        return
    try:
        client.groups.add_single_subscriber(group_id, author_email)
        logger.info(f"Added {author_email} to MailerLite Pending group.")
    except Exception as e:
        logger.error(f"MailerLite send_swap_request_notification failed: {e}")


def approve_swap_notification(author_email: str):
    """
    Called when the slot owner clicks **Accept**.
    Moves the subscriber from Pending → Approved group.
    """
    client = _get_client()
    pending_id = _group_id('PENDING')
    approved_id = _group_id('APPROVED')
    if client is None:
        return
    try:
        if pending_id:
            client.groups.remove_subscriber(pending_id, author_email)
        if approved_id:
            client.groups.add_single_subscriber(approved_id, author_email)
        logger.info(f"Moved {author_email} from Pending → Approved in MailerLite.")
    except Exception as e:
        logger.error(f"MailerLite approve_swap_notification failed: {e}")


def reject_swap_notification(author_email: str):
    """
    Called when the slot owner clicks **Decline**.
    Removes the subscriber from Pending and tags them as Rejected.
    """
    client = _get_client()
    pending_id = _group_id('PENDING')
    rejected_id = _group_id('REJECTED')
    if client is None:
        return
    try:
        if pending_id:
            client.groups.remove_subscriber(pending_id, author_email)
        if rejected_id:
            client.groups.add_single_subscriber(rejected_id, author_email)
        logger.info(f"Moved {author_email} to Rejected group in MailerLite.")
    except Exception as e:
        logger.error(f"MailerLite reject_swap_notification failed: {e}")
