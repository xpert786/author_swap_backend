from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import PasswordResetToken, UserProfile, Subgenre, AudienceTag
from .constants import PRIMARY_GENRE_CHOICES, ALL_SUBGENRES, AUDIENCE_TAG_CHOICES, GENRE_SUBGENRE_MAPPING, COLLABORATION_STATUS
import json

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"))
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Try to find user by email first
            try:
                user_obj = User.objects.get(email__iexact=email)
                # Authenticate using the username (since USERNAME_FIELD is username)
                user = authenticate(
                    request=self.context.get('request'),
                    username=user_obj.username,
                    password=password
                )
            except User.DoesNotExist:
                user = None

            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"))
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )
    confirm_password = serializers.CharField(
        label=_("Confirm Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return value

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')

        if password != confirm_password:
            raise serializers.ValidationError({"confirm_password": _("Passwords do not match.")})

        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user = User.objects.create_user(username=username, email=email, password=password)
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"))

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(_("No user found with this email address."))
        return value


class VerifyOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(label=_("OTP"), max_length=6)

    def validate(self, attrs):
        otp = attrs.get('otp')
        try:
            reset_token = PasswordResetToken.objects.get(otp=otp, is_used=False)
            attrs['reset_token'] = reset_token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"otp": _("Invalid or expired OTP.")})
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"))
    new_password = serializers.CharField(
        label=_("New Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )
    confirm_password = serializers.CharField(
        label=_("Confirm Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )

    def validate(self, attrs):
        email = attrs.get('email')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": _("No user found with this email address.")})

        # Find the most recent unused token for this user
        reset_token = PasswordResetToken.objects.filter(user=user, is_used=False).order_by('-created_at').first()
        if not reset_token:
            raise serializers.ValidationError({"email": _("No valid reset token found. Please request a new OTP.")})

        attrs['user'] = user
        attrs['reset_token'] = reset_token

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": _("Passwords do not match.")})

        return attrs


class AccountBasicsSerializer(serializers.ModelSerializer):
    primary_genre = serializers.MultipleChoiceField(
        choices=PRIMARY_GENRE_CHOICES,
        required=False
    )
    subgenres = serializers.SlugRelatedField(
        many=True,
        slug_field='slug',
        queryset=Subgenre.objects.all(),
        required=False
    )
    audience_tags = serializers.SlugRelatedField(
        many=True,
        slug_field='name',
        queryset=AudienceTag.objects.all(),
        required=False
    )
    # Temporary field for incoming genre selection if needed by frontend
    genre_preferences = serializers.MultipleChoiceField(
        choices=PRIMARY_GENRE_CHOICES,
        required=False,
        write_only=True
    )

    class Meta:
        model = UserProfile
        fields = [
            "pen_name",
            "author_bio",
            "profile_photo",
            "primary_genre",
            "subgenres",
            "audience_tags",
            "genre_preferences",
        ]

    def validate_primary_genre(self, value):
        if value:
            return ",".join(value)
        return ""

    def validate_genre_preferences(self, value):
        if value:
            return ",".join(value)
        return ""

    def validate_subgenres(self, value):
        if len(value) > 3:
            raise serializers.ValidationError("Maximum 3 subgenres allowed.")
        return value

    def validate(self, data):
        primary_genre_str = data.get('primary_genre')
        subgenres_list = data.get('subgenres', [])

        if primary_genre_str and subgenres_list:
            # Validate that subgenres belong to the selected primary genres
            primary_genres = [g.strip() for g in primary_genre_str.split(',') if g.strip()]
            valid_subgenres = []
            for pg in primary_genres:
                valid_subgenres.extend([s.slug for s in Subgenre.objects.filter(parent_genre=pg)])
            
            for sub in subgenres_list:
                if sub.slug not in valid_subgenres:
                    raise serializers.ValidationError({
                        "subgenres": f"'{sub.name}' is not a valid subgenre for the selected categories."
                    })
        return data

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get('primary_genre') and isinstance(ret['primary_genre'], str):
            ret['primary_genre'] = [g.strip() for g in ret['primary_genre'].split(',') if g.strip()]
        return ret


class OnlinePresenceSerializer(serializers.ModelSerializer):
    website_url = serializers.URLField(required=False, allow_blank=True)
    collaboration_status = serializers.ChoiceField(choices=COLLABORATION_STATUS, required=False)

    def validate_collaboration_status(self, value):
        """Normalize input: allow labels OR keys, and make case-insensitive"""
        val_lower = value.lower()
        
        # Check against keys
        keys = [c[0] for c in COLLABORATION_STATUS]
        if val_lower in keys:
            return val_lower
            
        # Check against labels
        for key, label in COLLABORATION_STATUS:
            if val_lower == label.lower():
                return key
                
        # If no match, the standard ChoiceField validation will handle it, 
        # but let's provide a clear error if we reach here (unlikely)
        return value

    class Meta:
        model = UserProfile
        fields = ['website_url', 'facebook_url', 'instagram_url', 'tiktok_url', 'collaboration_status']


class UserProfileReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    subgenres = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )
    audience_tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'user_email', 'user_username', 'pen_name', 'author_bio', 
            'primary_genre', 'subgenres', 'audience_tags', 'profile_photo', 
            'website_url', 'facebook_url', 'instagram_url', 'tiktok_url', 
            'collaboration_status', 'created_at', 'updated_at'
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get('primary_genre') and isinstance(ret['primary_genre'], str):
            ret['primary_genre'] = [g.strip() for g in ret['primary_genre'].split(',') if g.strip()]
        return ret

class EditPenNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['pen_name']
