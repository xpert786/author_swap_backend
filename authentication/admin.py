from django.contrib import admin
from .models import UserProfile, PasswordResetToken, Subgenres, GenrePreference


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'pen_name', 'primary_genre', 'website_url', 'created_at']
    search_fields = ['user__username', 'user__email', 'pen_name']
    fields = ['user', 'pen_name', 'author_bio', 'primary_genre', 'subgenres', 'audience_tags',
              'website_url', 'facebook_url', 'instagram_url', 'tiktok_url','Collaboration_Status',
              'profile_photo', 'created_at', 'updated_at']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp', 'is_used', 'created_at']
    search_fields = ['user__email', 'otp']
    list_filter = ['is_used', 'created_at']



admin.site.register(Subgenres)
admin.site.register(GenrePreference)