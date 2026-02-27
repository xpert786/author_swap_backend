from django.contrib import admin
from .models import Profile, NewsletterSlot, Notification, SwapRequest, Book, SubscriberVerification, Email, ChatMessage
# Register your models here.
admin.site.register(Profile)
admin.site.register(NewsletterSlot)
admin.site.register(Notification)
admin.site.register(SwapRequest)
admin.site.register(Book)
admin.site.register(SubscriberVerification)


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['subject', 'sender', 'recipient', 'folder', 'is_read', 'is_draft', 'created_at']
    list_filter = ['folder', 'is_read', 'is_draft', 'is_starred']
    search_fields = ['subject', 'body', 'sender__username', 'recipient__username']
    ordering = ['-created_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'content', 'is_read', 'created_at']
    list_filter = ['is_read']
    search_fields = ['content', 'sender__username', 'recipient__username']
    ordering = ['-created_at']
