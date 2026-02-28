from django.contrib import admin
from .models import (
    Profile, NewsletterSlot, Notification, SwapRequest, Book, 
    SubscriberVerification, Email, ChatMessage, SubscriptionTier, 
    UserSubscription, SubscriberGrowth, CampaignAnalytic, SwapLinkClick
)

# Basic Registrations
admin.site.register(Profile)
admin.site.register(Notification)
admin.site.register(Book)
admin.site.register(SubscriberVerification)
admin.site.register(SubscriberGrowth)


@admin.register(NewsletterSlot)
class NewsletterSlotAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_genre', 'send_date', 'status', 'visibility', 'promotion_type']
    list_filter = ['status', 'visibility', 'promotion_type', 'preferred_genre']
    search_fields = ['user__username', 'preferred_genre']

@admin.register(SwapRequest)
class SwapRequestAdmin(admin.ModelAdmin):
    list_display = ['requester', 'slot', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['requester__username', 'slot__user__username']

@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'label', 'is_most_popular']
    search_fields = ['name']

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'tier', 'active_until', 'is_active']
    list_filter = ['is_active', 'tier']
    search_fields = ['user__username']

@admin.register(CampaignAnalytic)
class CampaignAnalyticAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'date', 'open_rate', 'click_rate', 'type']
    list_filter = ['type']
    search_fields = ['name', 'user__username']

@admin.register(SwapLinkClick)
class SwapLinkClickAdmin(admin.ModelAdmin):
    list_display = ['swap', 'link_name', 'clicks', 'ctr', 'conversions']
    search_fields = ['link_name', 'swap__requester__username']

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sender', 'recipient', 'folder', 'is_read', 'is_draft', 'created_at']
    list_filter = ['folder', 'is_read', 'is_draft', 'is_starred']
    search_fields = ['subject', 'body', 'sender__username', 'recipient__username']
    ordering = ['-created_at']

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'content', 'is_read', 'created_at']
    list_filter = ['is_read', 'is_file']
    search_fields = ['content', 'sender__username', 'recipient__username']
    ordering = ['-created_at']
