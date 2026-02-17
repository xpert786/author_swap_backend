from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
import secrets
import random

GENRE_PREFERENCES=[("primary", "Primary Genre"),
        ("subgenre", "Subgenre overlap"),
        ("tone", "Audience / Tone tags"),]
COLLABORATION_STATUS=[("Open to swaps","Invite only")]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    
    # Account Basics (Step 1)
    pen_name = models.CharField(max_length=100, blank=True, null=True)
    author_bio = models.TextField(blank=True, null=True)
    genre_preferences = models.CharField(max_length=100, choices=GENRE_PREFERENCES, blank=True, null=True)
    
    # Online Presence (Step 2)
    website_url = models.URLField(max_length=200, blank=True, null=True)
    facebook_url = models.URLField(max_length=200, blank=True, null=True)
    instagram_url = models.URLField(max_length=200, blank=True, null=True)
    tiktok_url = models.URLField(max_length=200, blank=True, null=True)
    Collaboration_Status=models.CharField(max_length=100, choices=COLLABORATION_STATUS, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        db_table = 'user_profile'


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        return self.otp

    def __str__(self):
        return f"OTP for {self.user.email}"

    class Meta:
        db_table = 'password_reset_token'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except User.profile.RelatedObjectDoesNotExist:
        UserProfile.objects.create(user=instance)


@receiver(pre_delete, sender=User)
def delete_user_related_data(sender, instance, **kwargs):
    """Clean up related data before user is deleted"""
    # Delete password reset tokens
    PasswordResetToken.objects.filter(user=instance).delete()
    # Delete profile
    try:
        instance.profile.delete()
    except User.profile.RelatedObjectDoesNotExist:
        pass
