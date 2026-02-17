from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import PasswordResetToken, UserProfile

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


class ResetPasswordSerializer(serializers.Serializer):
    otp = serializers.CharField(label=_("OTP"), max_length=6)
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
        otp = attrs.get('otp')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        try:
            reset_token = PasswordResetToken.objects.get(otp=otp, is_used=False)
            attrs['user'] = reset_token.user
            attrs['reset_token'] = reset_token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"otp": _("Invalid OTP.")})

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": _("Passwords do not match.")})

        return attrs


class AccountBasicsSerializer(serializers.ModelSerializer):
    pen_name = serializers.CharField(required=True, allow_blank=False)
    author_bio = serializers.CharField(required=True, allow_blank=False)
    genre_preferences = serializers.CharField(required=True, allow_blank=False)
    profile_photo = serializers.ImageField(required=True, allow_null=False)

    class Meta:
        model = UserProfile
        fields = ['pen_name', 'author_bio', 'profile_photo', 'genre_preferences']

    def validate_genre_preferences(self, value):
        valid_choices = ['primary', 'subgenre', 'tone']
        if value not in valid_choices:
            raise serializers.ValidationError(
                f"Invalid choice. Must be one of: Primary Genre (primary), Subgenre overlap (subgenre), Audience / Tone tags (tone)"
            )
        return value


class OnlinePresenceSerializer(serializers.ModelSerializer):
    website_url = serializers.URLField(required=True)
    facebook_url = serializers.URLField(required=True)
    instagram_url = serializers.URLField(required=True)
    tiktok_url = serializers.URLField(required=True)
    Collaboration_Status = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = UserProfile
        fields = ['website_url', 'facebook_url', 'instagram_url', 'tiktok_url', 'Collaboration_Status']

    def validate_Collaboration_Status(self, value):
        valid_choices = ['Open to swaps', 'Invite only']
        if value not in valid_choices:
            raise serializers.ValidationError(
                f"Invalid choice. Must be one of: {', '.join(valid_choices)}"
            )
        return value


class UserProfileReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'user_email', 'user_username', 'pen_name', 'author_bio', 
            'genre_preferences', 'profile_photo', 'website_url', 'facebook_url', 
            'instagram_url', 'tiktok_url', 'Collaboration_Status', 'created_at', 'updated_at'
        ]
