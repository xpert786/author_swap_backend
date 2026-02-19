from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import UserProfile, PasswordResetToken, Subgenres, GenrePreference, Subgenre, AudienceTag

class UserProfileForm(forms.ModelForm):
    def clean_subgenres(self):
        subgenres = self.cleaned_data.get('subgenres')
        if subgenres and subgenres.count() > 3:
            raise ValidationError("You can select a maximum of 3 subgenres.")
        return subgenres

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileForm
    list_display = ['user', 'pen_name', 'primary_genre', 'website_url', 'created_at']
    search_fields = ['user__username', 'user__email', 'pen_name']
    fields = ['user', 'pen_name', 'author_bio', 'primary_genre', 'subgenres', 'audience_tags',
              'website_url', 'facebook_url', 'instagram_url', 'tiktok_url', 'collaboration_status',
              'profile_photo', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp', 'is_used', 'created_at']
    search_fields = ['user__email', 'otp']
    list_filter = ['is_used', 'created_at']

admin.site.register(Subgenres)
admin.site.register(GenrePreference)
admin.site.register(Subgenre)
admin.site.register(AudienceTag)