from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
import secrets
import random
from django.core.exceptions import ValidationError

COLLABORATION_STATUS = [
    ("open", "Open to swaps"),
    ("invite", "Invite only"),
    ("closed", "Not accepting swaps"),
]

# =========================
# GENRE SCHEMA
# =========================

PRIMARY_GENRE_CHOICES = [
    ("romance", "Romance"),
    ("mystery_thriller", "Mystery / Thriller"),
    ("science_fiction", "Science Fiction"),
    ("fantasy", "Fantasy"),
    ("young_adult", "Young Adult"),
    ("childrens", "Children’s Books"),
    ("horror", "Horror"),
    ("literary", "Literary Fiction"),
    ("womens_fiction", "Women’s Fiction"),
    ("nonfiction", "Nonfiction"),
    ("action_adventure", "Action / Adventure"),
    ("comics_graphic", "Comics & Graphic Novels"),
]

AUDIENCE_TAG_CHOICES = [
    ("clean", "Clean / Sweet"),
    ("steamy", "Steamy"),
    ("explicit", "Explicit"),
    ("cozy", "Cozy"),
    ("dark", "Dark"),
    ("humor", "Humor-Forward"),
    ("faith", "Faith-Based / Christian"),
    ("holiday", "Holiday / Seasonal"),
    ("lgbtq", "LGBTQ+"),
    ("diverse", "Diverse / Inclusive"),
    ("series", "Series"),
    ("standalone", "Standalone"),
    ("short_reads", "Short Reads / Novellas"),
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)

    pen_name = models.CharField(max_length=100, blank=True, null=True)
    author_bio = models.TextField(blank=True, null=True)

    # Primary Genre
    primary_genre = models.CharField(
        max_length=50,
        choices=PRIMARY_GENRE_CHOICES,
        blank=True,
        null=True
    )

    # Store as comma-separated but validated
    subgenres = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        help_text="Comma separated values, max 3"
    )

    audience_tags = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        help_text="Comma separated values"
    )

    collaboration_status = models.CharField(
        max_length=10,
        choices=COLLABORATION_STATUS,
        default="open"
    )

    website_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 🔎 Helper Methods
    def get_subgenres_list(self):
        if self.subgenres:
            return self.subgenres.split(",")
        return []

    def get_audience_tags_list(self):
        if self.audience_tags:
            return self.audience_tags.split(",")
        return []

    # 🔒 Validation
    def clean(self):
        if self.subgenres:
            sub_list = self.subgenres.split(",")
            if len(sub_list) > 3:
                raise ValidationError("You can select a maximum of 3 subgenres")

    def __str__(self):
        return f"{self.user.username}'s Profile"

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


# Subgenre choices organized by primary genre
ROMANCE_SUBGENRES = [
    ('contemporary_romance', 'Contemporary Romance'),
    ('romantic_comedy', 'Romantic Comedy'),
    ('small_town_romance', 'Small Town Romance'),
    ('sports_romance', 'Sports Romance'),
    ('billionaire_romance', 'Billionaire Romance'),
    ('bad_boy_romance', 'Bad Boy Romance'),
    ('new_adult_romance', 'New Adult Romance'),
    ('erotic_romance', 'Erotic Romance / Erotica'),
    ('reverse_harem', 'Reverse Harem / Why Choose Romance'),
    ('paranormal_romance', 'Paranormal Romance'),
    ('romantic_suspense', 'Romantic Suspense'),
    ('dark_romance', 'Dark Romance'),
    ('historical_romance', 'Historical Romance'),
    ('western_romance', 'Western Romance'),
    ('military_romance', 'Military Romance'),
    ('medical_romance', 'Medical Romance'),
    ('holiday_romance', 'Holiday Romance'),
    ('sci_fi_romance', 'Sci-Fi Romance'),
    ('fantasy_romance', 'Fantasy Romance'),
    ('lgbtq_romance', 'LGBTQ+ Romance'),
]

MYSTERY_THRILLER_SUBGENRES = [
    ('cozy_mystery', 'Cozy Mystery'),
    ('amateur_sleuth', 'Amateur Sleuth'),
    ('police_procedural', 'Police Procedural'),
    ('crime_thriller', 'Crime Thriller'),
    ('psychological_thriller', 'Psychological Thriller'),
    ('legal_thriller', 'Legal Thriller'),
    ('techno_thriller', 'Techno-Thriller'),
    ('suspense', 'Suspense'),
    ('historical_mystery', 'Historical Mystery'),
]

SCIENCE_FICTION_SUBGENRES = [
    ('space_opera', 'Space Opera'),
    ('military_sci_fi', 'Military Sci-Fi'),
    ('dystopian', 'Dystopian'),
    ('post_apocalyptic', 'Post-Apocalyptic'),
    ('time_travel', 'Time Travel'),
    ('hard_sci_fi', 'Hard Sci-Fi'),
    ('alien_first_contact', 'Alien / First Contact'),
    ('cyberpunk', 'Cyberpunk'),
]

FANTASY_SUBGENRES = [
    ('epic_high_fantasy', 'Epic / High Fantasy'),
    ('urban_fantasy', 'Urban Fantasy'),
    ('dark_fantasy', 'Dark Fantasy'),
    ('portal_fantasy', 'Portal Fantasy'),
    ('sword_sorcery', 'Sword & Sorcery'),
    ('mythology_retellings', 'Mythology / Retellings'),
    ('litrpg_gamelit', 'LitRPG / GameLit'),
]

YOUNG_ADULT_SUBGENRES = [
    ('ya_romance', 'YA Romance'),
    ('ya_fantasy', 'YA Fantasy'),
    ('ya_sci_fi', 'YA Sci-Fi'),
    ('ya_contemporary', 'YA Contemporary'),
    ('ya_mystery_thriller', 'YA Mystery / Thriller'),
    ('ya_paranormal', 'YA Paranormal'),
]

CHILDRENS_SUBGENRES = [
    ('picture_books', 'Picture Books'),
    ('early_readers', 'Early Readers'),
    ('chapter_books', 'Chapter Books'),
    ('middle_grade', 'Middle Grade'),
    ('educational', 'Educational'),
    ('comics_graphic_novels', 'Comics & Graphic Novels'),
]

HORROR_SUBGENRES = [
    ('psychological_horror', 'Psychological Horror'),
    ('supernatural_horror', 'Supernatural Horror'),
    ('paranormal_horror', 'Paranormal Horror'),
    ('dark_fantasy_horror', 'Dark Fantasy Horror'),
    ('thriller_horror', 'Thriller Horror'),
]

LITERARY_FICTION_SUBGENRES = [
    ('contemporary_literary', 'Contemporary Literary'),
    ('historical_literary', 'Historical Literary'),
    ('experimental', 'Experimental'),
]

WOMENS_FICTION_SUBGENRES = [
    ('contemporary_womens', 'Contemporary Women\'s Fiction'),
    ('book_club_fiction', 'Book Club Fiction'),
    ('family_relationships', 'Family / Relationships'),
    ('emotional_dramatic', 'Emotional / Dramatic'),
]

NONFICTION_SUBGENRES = [
    ('memoir_biography', 'Memoir / Biography'),
    ('self_help', 'Self-Help / Personal Development'),
    ('business_finance', 'Business / Finance'),
    ('health_wellness', 'Health & Wellness'),
    ('parenting_family', 'Parenting / Family'),
    ('faith_spirituality', 'Faith / Spirituality'),
    ('education', 'Education'),
    ('writing_publishing', 'Writing / Publishing'),
]

ACTION_ADVENTURE_SUBGENRES = [
    ('military_war', 'Military / War'),
    ('espionage', 'Espionage'),
    ('survival', 'Survival'),
    ('adventure_thriller', 'Adventure Thriller'),
]

COMICS_GRAPHIC_NOVELS_SUBGENRES = [
    ('fiction', 'Fiction'),
    ('nonfiction', 'Nonfiction'),
    ('childrens', 'Children\'s'),
    ('manga', 'Manga'),
]

# Mapping of primary genres to their subgenres
GENRE_SUBGENRE_MAPPING = {
    'romance': ROMANCE_SUBGENRES,
    'mystery_thriller': MYSTERY_THRILLER_SUBGENRES,
    'science_fiction': SCIENCE_FICTION_SUBGENRES,
    'fantasy': FANTASY_SUBGENRES,
    'young_adult': YOUNG_ADULT_SUBGENRES,
    'childrens': CHILDRENS_SUBGENRES,
    'horror': HORROR_SUBGENRES,
    'literary': LITERARY_FICTION_SUBGENRES,
    'womens_fiction': WOMENS_FICTION_SUBGENRES,
    'nonfiction': NONFICTION_SUBGENRES,
    'action_adventure': ACTION_ADVENTURE_SUBGENRES,
    'comics_graphic': COMICS_GRAPHIC_NOVELS_SUBGENRES,
}

# All subgenres combined (for validation)
ALL_SUBGENRES = (
    ROMANCE_SUBGENRES + MYSTERY_THRILLER_SUBGENRES + SCIENCE_FICTION_SUBGENRES +
    FANTASY_SUBGENRES + YOUNG_ADULT_SUBGENRES + CHILDRENS_SUBGENRES + HORROR_SUBGENRES +
    LITERARY_FICTION_SUBGENRES + WOMENS_FICTION_SUBGENRES + NONFICTION_SUBGENRES +
    ACTION_ADVENTURE_SUBGENRES + COMICS_GRAPHIC_NOVELS_SUBGENRES
)


class GenrePreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='genre_preferences')
    genre = models.CharField(max_length=50, choices=PRIMARY_GENRE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Genre Preference"
    

class Subgenres(models.Model):
    genre_preference = models.ForeignKey(GenrePreference, on_delete=models.CASCADE, related_name='genre_preference')
    subgenre = models.CharField(max_length=50, choices=GENRE_SUBGENRE_MAPPING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.genre_preference.user.username}'s Subgenre"

    @staticmethod
    def get_subgenres_by_primary_genre(primary_genre):
        """Get subgenres choices based on primary genre"""
        return GENRE_SUBGENRE_MAPPING.get(primary_genre, [])