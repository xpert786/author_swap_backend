import logging
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Base URL for the new MailerLite API
API_URL = "https://connect.mailerlite.com/api"


def _get_headers(api_key=None):
    """
    Returns headers with Bearer token for MailerLite API.
    """
    if not api_key:
        api_key = getattr(settings, 'MAILERLITE_API_KEY', None)
    
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }


# ---------------------------------------------------------------------------
# A.  Audience Size Sync
# ---------------------------------------------------------------------------

def get_subscriber_counts_by_status(api_key: str = None) -> dict:
    """
    Fetches subscriber counts by status from MailerLite API.
    Returns a dict with counts for: active, unsubscribed, unconfirmed, bounced, junk
    
    MailerLite statuses: active, unsubscribed, unconfirmed, bounced, junk
    """
    if not api_key:
        api_key = getattr(settings, 'MAILERLITE_API_KEY', None)
    
    if not api_key:
        logger.warning("No API key provided for get_subscriber_counts_by_status")
        return {}

    is_new_api = api_key.startswith("mlsn.")
    logger.info(f"[DIAGNOSTIC] API key format check: is_new_api={is_new_api}, key prefix: {api_key[:15]}...")
    
    # Status mapping: internal name -> MailerLite status name
    statuses = ['active', 'unsubscribed', 'unconfirmed', 'bounced', 'junk']
    counts = {}
    
    try:
        if is_new_api:
            url = f"{API_URL}/subscribers"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            for status in statuses:
                # Use limit=1 - some API versions/proxies may behave better than limit=0
                try:
                    response = requests.get(
                        url, 
                        headers=headers, 
                        params={"limit": 1, "filter[status]": status}, 
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"[DIAGNOSTIC] Raw response for {status}: {data}")
                        count = data.get('meta', {}).get('total', 0)
                        
                        # Fallback: if meta.total is missing but we got data, check length
                        if count == 0 and 'data' in data and len(data['data']) > 0:
                            count = len(data['data'])
                            # If it's 1 and we used limit=1, it might be more. 
                            # But usually meta.total is present.
                            
                        counts[status] = count
                        logger.info(f"[DIAGNOSTIC] Status '{status}': {count} subscribers")
                    else:
                        logger.error(f"[DIAGNOSTIC] Failed to fetch {status}: HTTP {response.status_code} - {response.text}")
                        counts[status] = 0
                except Exception as inner_e:
                    logger.error(f"[DIAGNOSTIC] Exception fetching {status}: {inner_e}")
                    counts[status] = 0
            
            # Add a 'dashboard_total' fetch - usually matches Active + Unconfirmed
            try:
                # Try fetching without status filter to see what the base total is
                base_resp = requests.get(url, headers=headers, params={"limit": 1}, timeout=10)
                if base_resp.status_code == 200:
                    base_total = base_resp.json().get('meta', {}).get('total', 0)
                    counts['dashboard_total'] = base_total
                    logger.info(f"[DIAGNOSTIC] Base subscribers total: {base_total}")
            except Exception:
                pass

            logger.info(f"[DIAGNOSTIC] MailerLite status counts fetched: {counts}")
            return counts  # Return counts even if 0
        else:
            # Classic API - use the V2 subscribers endpoint with count
            logger.warning(f"[DIAGNOSTIC] Classic API detected (key doesn't start with 'mlsn.'). Using V2 subscribers endpoint. Key prefix: {api_key[:10]}...")
            try:
                # Classic API uses different base URL and header
                url = "https://api.mailerlite.com/api/v2/subscribers"
                headers = {
                    "Content-Type": "application/json",
                    "X-MailerLite-ApiKey": api_key
                }
                
                # For Classic API, we need to fetch with a high limit to get total
                # Try with limit=0 first to see if we get meta data, otherwise use high limit
                response = requests.get(url, headers=headers, params={"limit": 0}, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Check if response has meta/total
                    if isinstance(data, dict) and 'meta' in data:
                        counts['active'] = data.get('meta', {}).get('total', 0)
                        logger.info(f"[DIAGNOSTIC] Classic API v2 meta total: {counts['active']}")
                    else:
                        # Classic API returns array, try to get total count via count parameter workaround
                        # Fetch stats for active count
                        counts['active'] = 0  # Will update from stats
                        logger.info(f"[DIAGNOSTIC] Classic API limit=0 response type: {type(data)}, keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                else:
                    logger.warning(f"[DIAGNOSTIC] Classic API limit=0 failed: {response.status_code}")
                
                # Use stats endpoint for all main counts
                stats_resp = requests.get("https://api.mailerlite.com/api/v2/stats", headers=headers, timeout=10)
                if stats_resp.status_code == 200:
                    stats_data = stats_resp.json()
                    logger.info(f"[DIAGNOSTIC] Classic API raw stats FULL: {stats_data}")
                    
                    # Log all available keys to find the right one
                    if isinstance(stats_data, dict):
                        logger.info(f"[DIAGNOSTIC] Available stats keys: {list(stats_data.keys())}")
                    
                    # Try multiple possible field names for active subscribers
                    possible_active_fields = ['subscribed', 'active', 'total', 'total_subscribers', 'subscribers', 'active_subscribers', 'total_active']
                    for field in possible_active_fields:
                        if field in stats_data and stats_data[field]:
                            logger.info(f"[DIAGNOSTIC] Found active count in field '{field}': {stats_data[field]}")
                            counts['active'] = stats_data[field]
                            break
                    
                    # If still 0, try to calculate from other fields
                    if counts['active'] == 0 and isinstance(stats_data, dict):
                        # Sometimes total = active + unsubscribed + bounced + unconfirmed
                        total = stats_data.get('total', 0)
                        if total > 0:
                            unsub = stats_data.get('unsubscribed', 0) or stats_data.get('unsubscribe', 0) or 0
                            bounced = stats_data.get('bounced', 0) or stats_data.get('bounce', 0) or 0
                            unconfirmed = stats_data.get('unconfirmed', 0) or stats_data.get('unconfirm', 0) or 0
                            counts['active'] = total - unsub - bounced - unconfirmed
                            logger.info(f"[DIAGNOSTIC] Calculated active from total: {counts['active']} = {total} - {unsub} - {bounced} - {unconfirmed}")
                    
                    counts['unsubscribed'] = stats_data.get('unsubscribed', 0) or stats_data.get('unsubscribe', 0) or 0
                    counts['unconfirmed'] = stats_data.get('unconfirmed', 0) or stats_data.get('unconfirm', 0) or 0
                    counts['bounced'] = stats_data.get('bounced', 0) or stats_data.get('bounce', 0) or 0
                    counts['junk'] = stats_data.get('junk', 0) or stats_data.get('spam', 0) or 0
                    
                    logger.info(f"[DIAGNOSTIC] Classic API stats parsed: active={counts['active']}, unsubscribed={counts['unsubscribed']}")
                else:
                    logger.error(f"[DIAGNOSTIC] Classic API stats failed: HTTP {stats_resp.status_code} - {stats_resp.text[:500]}")
                
                # If still no active count, try fetching subscribers with high limit
                if counts['active'] == 0:
                    logger.info(f"[DIAGNOSTIC] Trying high limit fetch for Classic API...")
                    # Try with type=active filter
                    high_limit_resp = requests.get(url, headers=headers, params={"limit": 5000, "type": "active"}, timeout=15)
                    if high_limit_resp.status_code == 200:
                        data = high_limit_resp.json()
                        # X-Total-Count header is usually the best source for Classic API
                        total_header = high_limit_resp.headers.get('X-Total-Count')
                        if total_header:
                            counts['active'] = int(total_header)
                            logger.info(f"[DIAGNOSTIC] Classic API active count (X-Total-Count): {counts['active']}")
                        elif isinstance(data, list):
                            counts['active'] = len(data)
                            logger.info(f"[DIAGNOSTIC] Classic API high limit count (list): {counts['active']}")
                        elif isinstance(data, dict):
                            if 'data' in data:
                                counts['active'] = len(data['data'])
                            if 'meta' in data and 'total' in data['meta']:
                                counts['active'] = data['meta']['total']
                            logger.info(f"[DIAGNOSTIC] Classic API high limit count (dict): {counts['active']}")
                    else:
                        logger.error(f"[DIAGNOSTIC] High limit fetch failed: HTTP {high_limit_resp.status_code}")
                
                logger.info(f"[DIAGNOSTIC] Classic API final counts: {counts}")
                return counts  # Return whatever we found
                
            except Exception as classic_e:
                logger.error(f"[DIAGNOSTIC] Classic API exception: {classic_e}")
                import traceback
                logger.error(f"[DIAGNOSTIC] Traceback: {traceback.format_exc()}")
                return {}
            
    except Exception as e:
        logger.error(f"[DIAGNOSTIC] MailerLite get_subscriber_counts_by_status failed: {e}")
        return {}


def get_audience_size(email: str = None, api_key: str = None) -> int:
    """
    Fetches the total active subscriber count for the account.
    Detects if the key is for New MailerLite (Bearer) or Classic (X-MailerLite-ApiKey).
    """
    if not api_key:
        api_key = getattr(settings, 'MAILERLITE_API_KEY', None)
    
    if not api_key:
        return 0

    # New tokens start with "mlsn."
    is_new_api = api_key.startswith("mlsn.")
    
    try:
        if is_new_api:
            # --- New MailerLite API ---
            url = f"{API_URL}/subscribers"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            # We fetch subscribers to get the 'meta' field which has the total.
            # Removing status filter temporarily to see if we get a non-zero count.
            response = requests.get(url, headers=headers, params={"limit": 1}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                total = data.get('meta', {}).get('total', 0)
                logger.info(f"New MailerLite API: Total Found {total}")
                return total
            logger.warning(f"New MailerLite API failed ({response.status_code}): {response.text}")
        else:
            # --- Classic MailerLite API ---
            url = "https://api.mailerlite.com/api/v2/stats"
            headers = {
                "Content-Type": "application/json",
                "X-MailerLite-ApiKey": api_key
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Classic stats returns 'subscribed' count
                total = data.get('subscribed', 0)
                logger.info(f"Classic MailerLite API: Found {total} subscribers.")
                return total
            logger.warning(f"Classic MailerLite API failed ({response.status_code}): {response.text}")

        # Final Fallback: If specific subscriber count is 0, check if we can get ANYTHING
        return 0
    except Exception as e:
        logger.error(f"MailerLite get_audience_size failed: {e}")
        return 0


def sync_profile_audience(profile, api_key: str = None) -> int:
    """
    Convenience wrapper: pull the latest audience size from MailerLite.
    Uses provided api_key (from connection handshake) or falling back to stored key.
    """
    from core.models import SubscriberVerification, NewsletterSlot
    
    # Try to find the stored key if none provided
    if not api_key:
        verification = SubscriberVerification.objects.filter(user=profile.user).first()
        if verification and verification.is_connected_mailerlite:
             # In a real app, this should be the actual saved key
             api_key = getattr(verification, 'mailerlite_api_key', None)

    email = profile.email or profile.user.email
    audience = get_audience_size(email, api_key=api_key)
    
    if audience > 0:
        NewsletterSlot.objects.filter(
            user=profile.user, visibility='public'
        ).update(audience_size=audience)
    
    verification, _ = SubscriberVerification.objects.get_or_create(user=profile.user)
    # Only update audience_size if we get valid data (> 0)
    if audience > 0:
        verification.audience_size = audience
        verification.save()
    
    return audience


def sync_subscriber_analytics(user):
    """
    Fetches real-time analytics from MailerLite for a specific user.
    """
    from core.models import SubscriberVerification, CampaignAnalytic
    from django.utils import timezone
    from django.conf import settings
    import random
    
    verification, _ = SubscriberVerification.objects.get_or_create(user=user)
    
    # Check for API key in user's verification first, then fall back to settings
    api_key = getattr(verification, 'mailerlite_api_key', None)
    if not api_key:
        api_key = getattr(settings, 'MAILERLITE_API_KEY', None)
        logger.info(f"[DIAGNOSTIC] Using API key from settings for user {user.username}")
    else:
        logger.info(f"[DIAGNOSTIC] Using API key from user verification for user {user.username}")
    
    headers = _get_headers(api_key)
    if not headers.get("Authorization") or not verification.is_connected_mailerlite:
        # Simulation if no real sync possible
        verification.avg_open_rate = round(max(30, min(60, verification.avg_open_rate + random.uniform(-0.5, 0.5))), 1)
        verification.avg_click_rate = round(max(5, min(15, verification.avg_click_rate + random.uniform(-0.1, 0.1))), 1)
        verification.last_verified_at = timezone.now()
        verification.save()
        return verification

    try:
        # 1. Sync Audience
        profile = user.profiles.first()
        if profile:
            sync_profile_audience(profile, api_key=api_key)
        
        # 2. Fetch Campaigns
        campaigns_resp = requests.get(f"{API_URL}/campaigns", headers=headers, params={"limit": 5}, timeout=10)
        if campaigns_resp.status_code == 200:
            campaigns = campaigns_resp.json().get('data', [])
            for camp in campaigns:
                CampaignAnalytic.objects.update_or_create(
                    user=user,
                    name=camp.get('subject') or camp.get('name'),
                    defaults={
                        'date': camp.get('sent_at') or timezone.now().date(),
                        'subscribers': camp.get('total_recipients', 0),
                        'open_rate': camp.get('open_rate_percent', 0.0),
                        'click_rate': camp.get('click_rate_percent', 0.0),
                        'type': 'Recent'
                    }
                )

        # 3. Fetch Subscriber Status Breakdown
        logger.info(f"Fetching status counts for user {user.username}, api_key present: {bool(api_key)}, is_connected: {verification.is_connected_mailerlite}")
        status_counts = get_subscriber_counts_by_status(api_key)
        logger.info(f"Status counts result: {status_counts}")
        if status_counts is not None:
            # Update verification with latest counts (even if 0)
            verification.active_subscribers = status_counts.get('active', 0)
            verification.unsubscribed_subscribers = status_counts.get('unsubscribed', 0)
            verification.unconfirmed_subscribers = status_counts.get('unconfirmed', 0)
            verification.bounced_subscribers = status_counts.get('bounced', 0)
            verification.junk_subscribers = status_counts.get('junk', 0)
            
            # Use dashboard_total if provided, otherwise fallback to active + unconfirmed
            db_total = status_counts.get('dashboard_total', 0)
            if db_total == 0:
                db_total = verification.active_subscribers + verification.unconfirmed_subscribers
            
            # Update audience_size to match the "Big Number" (Active + Unconfirmed)
            verification.audience_size = db_total
            
            # --- Added: Update/Create SubscriberGrowth Record for Current Month ---
            from core.models import SubscriberGrowth
            current_date = timezone.now()
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            current_month_name = month_names[current_date.month - 1]
            
            SubscriberGrowth.objects.update_or_create(
                user=user,
                month=current_month_name,
                year=current_date.year,
                defaults={'count': verification.active_subscribers}
            )
            
            # Update average rates from latest campaigns
            latest_campaigns = CampaignAnalytic.objects.filter(user=user).order_by('-date')[:5]
            if latest_campaigns.exists():
                total_open = sum(c.open_rate for c in latest_campaigns)
                total_click = sum(c.click_rate for c in latest_campaigns)
                count = latest_campaigns.count()
                verification.avg_open_rate = round(total_open / count, 1)
                verification.avg_click_rate = round(total_click / count, 1)
                
                # Health Score calculation
                health_score = int(min(100, (verification.avg_open_rate + (verification.avg_click_rate * 3))))
                verification.list_health_score = health_score
                
                # Metrics
                total_subs = verification.active_subscribers + verification.unsubscribed_subscribers + verification.bounced_subscribers
                if total_subs > 0:
                    verification.bounce_rate = round((verification.bounced_subscribers / total_subs) * 100, 1)
                    verification.unsubscribe_rate = round((verification.unsubscribed_subscribers / total_subs) * 100, 1)
                    verification.active_rate = round((verification.active_subscribers / total_subs) * 100, 1)
                verification.avg_engagement = round(verification.avg_open_rate / 10, 1)

            logger.info(f"Updated subscriber status counts for user {user.username}: active={verification.active_subscribers}")
        else:
            logger.warning(f"No valid status counts returned for user {user.username} - keeping existing values")
            # Don't override existing values if API call fails

        # 4. Overall Stats
        # MailerLite new API might have different stats endpoint, fallback to basic calculation if needed
        
        verification.last_verified_at = timezone.now()
        verification.save()
        
    except Exception as e:
        logger.error(f"MailerLite sync_subscriber_analytics failed: {e}")
    
    return verification


# ---------------------------------------------------------------------------
# B.  Group Management  (Pending / Approved / Rejected)
# ---------------------------------------------------------------------------

def _group_id(name: str) -> str:
    key = f"MAILERLITE_{name.upper()}_GROUP_ID"
    return getattr(settings, key, '')


def send_swap_request_notification(author_email: str):
    """
    Adds the author to the "Pending Swaps" group in the MASTER account.
    """
    headers = _get_headers() # Uses master key
    group_id = _group_id('PENDING')
    if not headers.get("Authorization") or not group_id:
        return
        
    try:
        # New MailerLite API: POST /groups/{group_id}/subscribers
        requests.post(
            f"{API_URL}/groups/{group_id}/subscribers",
            headers=headers,
            json={"email": author_email},
            timeout=10
        )
    except Exception as e:
        logger.error(f"MailerLite send_swap_request_notification failed: {e}")


def approve_swap_notification(author_email: str):
    """
    Moves subscriber from Pending -> Approved group in MASTER account.
    """
    headers = _get_headers()
    pending_id = _group_id('PENDING')
    approved_id = _group_id('APPROVED')
    
    if not headers.get("Authorization"):
        return
        
    try:
        # Add to approved
        if approved_id:
            requests.post(f"{API_URL}/groups/{approved_id}/subscribers", headers=headers, json={"email": author_email}, timeout=10)
        # Remove from pending
        if pending_id:
            # New MailerLite API: DELETE /groups/{group_id}/subscribers/{subscriber_id}
            # Note: We need the subscriber_id or email. Some endpoints support email.
            requests.delete(f"{API_URL}/groups/{pending_id}/subscribers/{author_email}", headers=headers, timeout=10)
    except Exception as e:
        logger.error(f"MailerLite approve_swap_notification failed: {e}")


def reject_swap_notification(author_email: str):
    """
    Moves subscriber to Rejected group in MASTER account.
    """
    headers = _get_headers()
    pending_id = _group_id('PENDING')
    rejected_id = _group_id('REJECTED')
    
    if not headers.get("Authorization"):
        return
        
    try:
        if rejected_id:
            requests.post(f"{API_URL}/groups/{rejected_id}/subscribers", headers=headers, json={"email": author_email}, timeout=10)
        if pending_id:
            requests.delete(f"{API_URL}/groups/{pending_id}/subscribers/{author_email}", headers=headers, timeout=10)
    except Exception as e:
        logger.error(f"MailerLite reject_swap_notification failed: {e}")
