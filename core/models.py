from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from authentication.constants import PRIMARY_GENRE_CHOICES

User = get_user_model()

class NewsletterSlot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='newsletter_slots')
    send_date = models.DateField()
    send_time = models.TimeField(blank=True, null=True)  
    status = models.CharField(max_length=20, choices=[('available', 'Available'), ('booked', 'Booked'),('pending', 'Pending')], default='available')    
    @property
    def time_period(self):
        if not self.send_time:
            return "Flexible"
        hour = self.send_time.hour
        if 0 <= hour < 12:
            return "Morning"    
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"
    audience_size = models.PositiveIntegerField(default=0, blank=True, null=True)
    preferred_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    
    # Store subgenres as a comma-separated string
    subgenres = models.CharField(max_length=300, blank=True, null=True)
    max_partners = models.PositiveIntegerField(default=5)
    visibility = models.CharField(
        max_length=30, 
        choices=[('public', 'Public'), ('friend_only', 'Friend Only'),('single_use_private_link', 'Single-use private link'),('hidden', 'Hidden')], 
        default='public'
    )
    
    # Advanced Discovery Fields
    PLACEMENT_CHOICES = [('top', 'Top'), ('mid', 'Mid'), ('bottom', 'Bottom'), ('any', 'Any')]
    placement_style = models.CharField(max_length=20, choices=PLACEMENT_CHOICES, default='any')
    
    PROMOTION_CHOICES = [('free', 'Free'), ('paid', 'Paid'), ('genre_specific', 'Genre-Specific')]
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_CHOICES, default='genre_specific')
    
    # Added price for paid promotions based on UI mockups
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True, null=True, help_text="Set price if promotion_type is Paid")
    
    partner_requirements = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):   
        return f"{self.preferred_genre} slot on {self.send_date}"

class Book(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=255)
    primary_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    subgenres = models.CharField(max_length=300, help_text="Comma-separated keys")
    rating = models.FloatField(default=0.0, null=True, blank=True)
    price_tier = models.CharField(max_length=50, blank=True, null=True, choices=[('discount', 'Discount'), ('free', 'Free'), ('standard', 'Standard'), ('0.99', '$0.99')], default='standard')
    book_cover = models.ImageField(upload_to='book_covers/', blank=True, null=True, max_length=255)
    availability = models.CharField(max_length=50,choices=[('all','All'),('wide','Wide'),('kindle_unlimited','Kindle Unlimited')],default='all')
    publish_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, default='')    
    # Retailer Links
    amazon_url = models.URLField(blank=True, null=True)
    apple_url = models.URLField(blank=True, null=True)
    kobo_url = models.URLField(blank=True, null=True)
    barnes_noble_url = models.URLField(blank=True, null=True)

    is_primary_promo = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')
    email = models.EmailField(blank=True, null=True)
    name = models.CharField(max_length=100)
    pen_name = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True, max_length=255)
    location = models.CharField(max_length=100, blank=True, null=True)
    primary_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    instagram_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    reputation_score = models.FloatField(default=0.0) # 0 to 100 based on mockup
    
    # Analytics Breakdown (Mockup Details)
    avg_open_rate = models.FloatField(default=0.0)
    avg_click_rate = models.FloatField(default=0.0)
    monthly_growth = models.PositiveIntegerField(default=0)
    send_reliability_percent = models.FloatField(default=0.0)
    
    # Reputation Score Breakdown
    confirmed_sends_score = models.PositiveIntegerField(default=0)
    timeliness_score = models.PositiveIntegerField(default=0)
    missed_sends_penalty = models.IntegerField(default=0)
    communication_score = models.PositiveIntegerField(default=0)
    
    # Advanced Reputation fields (Author Reputation System)
    is_webhook_verified = models.BooleanField(default=True)
    platform_ranking_position = models.PositiveIntegerField(default=0)
    platform_ranking_percentile = models.PositiveIntegerField(default=0)
    confirmed_sends_success_rate = models.FloatField(default=0.0)
    timeliness_success_rate = models.FloatField(default=0.0)
    missed_sends_count = models.PositiveIntegerField(default=0)
    avg_response_time_hours = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def swaps_completed(self):
        from .models import SwapRequest
        # Count confirmed/verified requests where this profile's user is either the requester or the slot owner
        sent_confirmed = self.user.sent_swap_requests.filter(status__in=['confirmed', 'verified', 'scheduled', 'completed']).count()
        received_confirmed = SwapRequest.objects.filter(slot__user=self.user, status__in=['confirmed', 'verified', 'scheduled', 'completed']).count()
        return sent_confirmed + received_confirmed

    # Auto-Approve logic and friends
    auto_approve_friends = models.BooleanField(default=False)
    auto_approve_min_reputation = models.FloatField(default=0.0)
    friends = models.ManyToManyField('self', blank=True, symmetrical=True)

class SubscriptionTier(models.Model):
    name = models.CharField(max_length=50) # Tier 1, Tier 2, etc.
    price = models.DecimalField(max_digits=10, decimal_places=2)
    label = models.CharField(max_length=50, blank=True) # Swap Only, Starter, etc.
    is_most_popular = models.BooleanField(default=False)
    features = models.JSONField(default=list) # List of feature strings
    best_for = models.TextField(blank=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.name

class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.PROTECT)
    active_until = models.DateField()
    renew_date = models.DateField()
    is_active = models.BooleanField(default=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.tier.name}"

class SubscriberVerification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification')
    is_connected_mailerlite = models.BooleanField(default=False)
    mailerlite_api_key = models.TextField(blank=True, null=True, help_text="Stored for syncing purposes. Should be encrypted in production.")
    mailerlite_api_key_last_4 = models.CharField(max_length=4, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    audience_size = models.PositiveIntegerField(default=0)
    avg_open_rate = models.FloatField(default=0)
    avg_click_rate = models.FloatField(default=0)
    list_health_score = models.PositiveIntegerField(default=0)
    
    # Health Metrics
    bounce_rate = models.FloatField(default=0)
    unsubscribe_rate = models.FloatField(default=0)
    active_rate = models.FloatField(default=0)
    avg_engagement = models.FloatField(default=0)
    
    # Subscriber Status Breakdown (for MailerLite API analytics)
    active_subscribers = models.PositiveIntegerField(default=0)
    unsubscribed_subscribers = models.PositiveIntegerField(default=0)
    unconfirmed_subscribers = models.PositiveIntegerField(default=0)
    bounced_subscribers = models.PositiveIntegerField(default=0)
    junk_subscribers = models.PositiveIntegerField(default=0, help_text="Spam/junk flagged subscribers")
    
    def __str__(self):
        return f"{self.user.username} Verification"

class SubscriberGrowth(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriber_growth')
    month = models.CharField(max_length=10) # Jan, Feb, etc.
    count = models.PositiveIntegerField()
    year = models.PositiveIntegerField(default=2024)

    class Meta:
        ordering = ['year', 'id']

class CampaignAnalytic(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaign_analytics')
    name = models.CharField(max_length=255) # June Newsletter - Romance Special
    date = models.DateField()
    subscribers = models.PositiveIntegerField()
    open_rate = models.FloatField()
    click_rate = models.FloatField()
    type = models.CharField(max_length=50, default='Recent') # Recent, Top Performing, Swap Campaigns
    
    def __str__(self):
        return self.name

class SwapRequest(models.Model):
    # The slot being requested (owned by *another* user)
    slot = models.ForeignKey(NewsletterSlot, on_delete=models.CASCADE, related_name='swap_requests')
    
    # The user making the request
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_swap_requests')
    
    # The book being promoted in this swap ("You Send" book)
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='swap_requests', null=True)

    # The slot the requester is offering in return ("You Send" slot)
    offered_slot = models.ForeignKey(NewsletterSlot, on_delete=models.SET_NULL, related_name='offered_swap_requests', null=True, blank=True)
    
    # The book the requester wants the partner to promote ("Partner Sends" book)
    requested_book = models.ForeignKey('Book', on_delete=models.SET_NULL, related_name='requested_in_swaps', null=True, blank=True)

    
    # The status of the request
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('sending', 'Sending'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # UI Modal Fields
    message = models.TextField(max_length=250, blank=True, null=True)
    PLACEMENT_CHOICES = [('top', 'Top'), ('middle', 'Middle'), ('bottom', 'Bottom')]
    preferred_placement = models.CharField(max_length=10, choices=PLACEMENT_CHOICES, default='middle')
    max_partners_acknowledged = models.PositiveIntegerField(default=5)

    # Rejection
    rejection_reason = models.TextField(blank=True, null=True)
    rejected_at = models.DateTimeField(blank=True, null=True)

    # Scheduling
    scheduled_date = models.DateField(blank=True, null=True)
    
    # Completion
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Tracking for Reputation (New)
    tracking_number = models.CharField(max_length=100, blank=True, null=True, help_text="Campaign ID or Send confirmation ID")
    shipped_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Request by {self.requester} for slot {self.slot}"


class SwapLinkClick(models.Model):
    """
    Tracks link-level CTR analysis for completed swaps.
    Each row = one tracked link in the swap partner's newsletter.
    Shown on the 'View Swap History' detail page (Figma).
    """
    swap = models.ForeignKey(SwapRequest, on_delete=models.CASCADE, related_name='link_clicks')
    link_name = models.CharField(max_length=255, help_text="e.g. 'The Midnight Garden'")
    destination_url = models.URLField(help_text="e.g. https://amazon.com/dp/B0C123456")
    clicks = models.PositiveIntegerField(default=0)
    ctr = models.FloatField(default=0.0, help_text="Click-through rate as percentage, e.g. 4.1")
    ctr_label = models.CharField(max_length=20, blank=True, default='', help_text="e.g. 'Excellent', 'Good', 'Low'")
    conversions = models.PositiveIntegerField(default=0, help_text="Number of sales/conversions")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.link_name} → {self.clicks} clicks ({self.ctr}%)"


class Notification(models.Model):
    # Badge labels as seen in image
    BADGE_CHOICES = [
        ('SWAP', 'Swap'),
        ('VERIFIED', 'Verified'),
        ('REMINDER', 'Reminder'),
        ('DEADLINE', 'Deadline'),
        ('NEW', 'New'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)  # e.g., "New Swap Request"
    message = models.TextField()              # e.g., "Amanda Johnson requested a swap..."
    badge = models.CharField(max_length=20, choices=BADGE_CHOICES, blank=True)
    
    # Actionable link (URL to jump to Message/Swap Detail)
    action_url = models.CharField(max_length=255, blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} for {self.recipient.username}"


class Email(models.Model):
    """
    Internal email/messaging system for Communication Tools.
    Authors can send emails to other authors on the platform.
    """
    FOLDER_CHOICES = [
        ('inbox', 'Inbox'),
        ('snoozed', 'Snoozed'),
        ('sent', 'Sent'),
        ('drafts', 'Drafts'),
        ('spam', 'Spam'),
        ('trash', 'Trash'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_emails')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='received_emails')
    subject = models.CharField(max_length=255, blank=True, default='')
    body = models.TextField(blank=True, default='')
    folder = models.CharField(max_length=20, choices=FOLDER_CHOICES, default='inbox')
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    parent_email = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    attachment = models.FileField(upload_to='email_attachments/', blank=True, null=True, max_length=255)
    sent_at = models.DateTimeField(null=True, blank=True)
    snoozed_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        recipient_str = self.recipient.username
        return f"{self.subject or '(No subject)'} — {self.sender.username} → {recipient_str}"


class ChatMessage(models.Model):
    """
    Real-time chat messages between authors.
    Used in the Communication Tools > Message tab.
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, max_length=255)
    is_read = models.BooleanField(default=False)
    is_file = models.BooleanField(default=False) # Keep for frontend compatibility
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username}: {self.content[:40]}"


class SwapPayment(models.Model):
    """
    Tracks payments for paid swap requests.
    When a user requests a swap in a paid slot, they need to complete payment.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    swap_request = models.OneToOneField(SwapRequest, on_delete=models.CASCADE, related_name='payment')
    payer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swap_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Stripe fields
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Receiver confirmation fields
    receiver_confirmed = models.BooleanField(default=False)
    receiver_confirmed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Swap {self.swap_request.id} - {self.status}"

    def complete_payment(self):
        """Mark payment as completed and transfer money to receiver's wallet"""
        if self.status == 'pending':
            self.status = 'completed'
            self.paid_at = timezone.now()
            self.save()
            
            # Create a payment transaction and add money to receiver's wallet
            receiver = self.swap_request.slot.user
            transaction = PaymentTransaction.objects.create(
                sender=self.payer,
                receiver=receiver,
                amount=self.amount,
                transaction_type='swap_payment',
                swap_payment=self,
                swap_request=self.swap_request,
                description=f"Payment for swap request #{self.swap_request.id}"
            )
            
            # Complete the transaction (this adds money to receiver's wallet)
            transaction.complete_transaction()
            return True
        return False

    class Meta:
        ordering = ['-created_at']


class UserWallet(models.Model):
    """
    Tracks user's wallet balance and payment information.
    Each user has one wallet that accumulates payments from swap requests.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Stripe Connect account ID for receiving payments
    stripe_connect_account_id = models.CharField(max_length=100, blank=True, null=True)
    is_stripe_connected = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - ${self.balance}"

    def add_balance(self, amount):
        """Add amount to wallet balance"""
        self.balance = Decimal(str(self.balance)) + Decimal(str(amount))
        self.total_earned = Decimal(str(self.total_earned)) + Decimal(str(amount))
        self.save()

    def withdraw_balance(self, amount):
        """Withdraw amount from wallet balance"""
        if self.balance >= amount:
            self.balance = Decimal(str(self.balance)) - Decimal(str(amount))
            self.total_withdrawn = Decimal(str(self.total_withdrawn)) + Decimal(str(amount))
            self.save()
            return True
        return False


class PaymentTransaction(models.Model):
    """
    Tracks all payment transactions in the system.
    Records money movement between users and for swap payments.
    """
    TRANSACTION_TYPES = [
        ('swap_payment', 'Swap Payment'),
        ('direct_payment', 'Direct Payment'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_transactions', null=True, blank=True)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Related objects (optional)
    swap_payment = models.ForeignKey('SwapPayment', on_delete=models.SET_NULL, null=True, blank=True)
    swap_request = models.ForeignKey('SwapRequest', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Stripe references
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        sender_name = self.sender.username if self.sender else "System"
        return f"{sender_name} -> {self.receiver.username}: ${self.amount}"

    def complete_transaction(self):
        """Mark transaction as completed and update receiver's wallet"""
        if self.status == 'pending':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            
            # Add money to receiver's wallet ONLY if it's not a withdrawal
            # For withdrawals, we've already deducted from the sender's wallet in the view.
            if self.transaction_type != 'withdrawal':
                wallet, created = UserWallet.objects.get_or_create(user=self.receiver)
                wallet.add_balance(self.amount)
                
                # Create notification for receiver - money received
                from core.models import Notification
                Notification.objects.create(
                    recipient=self.receiver,
                    title="💰 Payment Received!",
                    badge="PAYMENT",
                    message=f"${self.amount} has been credited to your account from {self.sender.username}.",
                    action_url="/wallet"
                )
                
                # Update swap status if this is a swap payment
                if self.swap_request:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Transaction completed for swap {self.swap_request.id}, current status: {self.swap_request.status}")
                    
                    swap = self.swap_request
                    # Update swap status to completed if payment is done
                    if swap.status in ['pending', 'scheduled', 'confirmed', 'accepted']:
                        old_status = swap.status
                        swap.status = 'completed'
                        swap.completed_at = timezone.now()
                        swap.save()
                        
                        logger.info(f"Swap {swap.id} status updated from {old_status} to completed")
                        
                        # Create notification for swap completion
                        Notification.objects.create(
                            recipient=swap.requester,
                            title="✅ Swap Completed!",
                            badge="SWAP",
                            message=f"Your swap with {swap.slot.user.username} has been completed successfully.",
                            action_url=f"/dashboard/swaps/track/{swap.id}/"
                        )
                        
                        Notification.objects.create(
                            recipient=swap.slot.user,
                            title="✅ Swap Completed!",
                            badge="SWAP",
                            message=f"Your swap with {swap.requester.username} has been completed successfully.",
                            action_url=f"/dashboard/swaps/track/{swap.id}/"
                        )
                    else:
                        logger.warning(f"Swap {swap.id} not updated - status {swap.status} not in allowed list")
            
            # Create notification for sender - payment sent/deducted
            if self.sender and self.transaction_type != 'withdrawal':
                from core.models import Notification
                sender_wallet, _ = UserWallet.objects.get_or_create(user=self.sender)
                Notification.objects.create(
                    recipient=self.sender,
                    title="💳 Payment Sent",
                    badge="PAYMENT",
                    message=f"${self.amount} has been deducted from your account. Remaining balance: ${sender_wallet.balance}",
                    action_url="/wallet"
                )
            
            return True
        return False

    class Meta:
        ordering = ['-created_at']

