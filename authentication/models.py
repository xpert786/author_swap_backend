from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
import secrets
import random
from django.core.exceptions import ValidationError, ObjectDoesNotExist



from .constants import PRIMARY_GENRE_CHOICES, ALL_SUBGENRES, AUDIENCE_TAG_CHOICES, COLLABORATION_STATUS, GENRE_SUBGENRE_MAPPING

class Subgenre(models.Model):
    """Stores all subgenres, linked to a parent primary genre"""
    parent_genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.get_parent_genre_display()} -> {self.name}"

    class Meta:
        ordering = ['parent_genre', 'name']


class AudienceTag(models.Model):
    """Stores Audience/Tone tags (e.g., Steamy, Clean, LGBTQ+)"""
    name = models.CharField(max_length=50)
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    pen_name = models.CharField(max_length=100, blank=True, null=True)
    author_bio = models.TextField(blank=True, null=True)

    # 1. Primary Genre (Single Select)
    primary_genre = models.CharField(
        max_length=50,
        choices=PRIMARY_GENRE_CHOICES,
        help_text="Required: Your main genre",
        blank=True,
        null=True
    )

    # 2. Subgenres (Multi-select, max 3)
    # We use ManyToMany instead of comma-separated strings for better filtering
    subgenres = models.ManyToManyField(Subgenre, blank=True)

    # 3. Audience Tags (Multi-select)
    audience_tags = models.ManyToManyField(AudienceTag, blank=True)

    collaboration_status = models.CharField(
        max_length=20,
        choices=COLLABORATION_STATUS,   
        default="open to swap"
    )

    website_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Custom validation for business rules"""
        # Note: ManyToMany validation usually happens in forms/admin, 
        # but we can add a check here for extra safety.
        super().clean()
        
    def __str__(self):
        return self.pen_name or self.user.username

    class Meta:
        db_table = "user_profile"


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
def manage_user_profile(sender, instance, created, **kwargs):
    """Creates or updates profile whenever user is saved"""
    if created:
        UserProfile.objects.get_or_create(user=instance)
    elif hasattr(instance, 'profile'):
        instance.profile.save()


@receiver(pre_delete, sender=User)
def delete_user_related_data(sender, instance, **kwargs):
    """Clean up related data before user is deleted"""
    # Delete password reset tokens
    PasswordResetToken.objects.filter(user=instance).delete()
    # Delete profile
    if hasattr(instance, 'profile'):
        instance.profile.delete()




class GenrePreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='genre_preferences')
    genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Genre Preference"
    

class Subgenres(models.Model):
    genre_preference = models.ForeignKey(GenrePreference, on_delete=models.CASCADE, related_name='subgenres')
    # Use ALL_SUBGENRES here so the field knows all possible valid options
    subgenre = models.CharField(max_length=50, choices=ALL_SUBGENRES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.genre_preference.user.username}'s Subgenre"

    @staticmethod
    def get_subgenres_by_primary_genre(primary_genre):
        """Get subgenres choices based on primary genre"""
        return GENRE_SUBGENRE_MAPPING.get(primary_genre, [])