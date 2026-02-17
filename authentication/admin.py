from django.contrib import admin
from .models import UserProfile, PasswordResetToken


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'pen_name', 'genre_preferences', 'website_url', 'created_at']
    search_fields = ['user__username', 'user__email', 'pen_name']
    fields = ['user', 'pen_name', 'author_bio', 'genre_preferences', 
              'website_url', 'facebook_url', 'instagram_url', 'tiktok_url','Collaboration_Status',
              'profile_photo', 'created_at', 'updated_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp', 'is_used', 'created_at']
    search_fields = ['user__email', 'otp']
    list_filter = ['is_used', 'created_at']
