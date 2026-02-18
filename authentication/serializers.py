from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import PasswordResetToken, UserProfile, PRIMARY_GENRE_CHOICES, ALL_SUBGENRES, AUDIENCE_TAG_CHOICES, GENRE_SUBGENRE_MAPPING, COLLABORATION_STATUS
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
    primary_genre = serializers.ChoiceField(
        choices=PRIMARY_GENRE_CHOICES,
        required=True
    )

    subgenres = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )

    audience_tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
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
        ]

    #  Convert incoming strings to lists if needed
    def to_internal_value(self, data):
        data = data.copy()

        if isinstance(data.get("subgenres"), str):
            data["subgenres"] = [
                s.strip() for s in data["subgenres"].split(",") if s.strip()
            ]

        if isinstance(data.get("audience_tags"), str):
            data["audience_tags"] = [
                t.strip() for t in data["audience_tags"].split(",") if t.strip()
            ]

        return super().to_internal_value(data)

    # Convert stored comma-separated strings back to lists
    def to_representation(self, instance):
        rep = super().to_representation(instance)

        rep["subgenres"] = (
            [s.strip() for s in instance.subgenres.split(",")]
            if instance.subgenres else []
        )

        rep["audience_tags"] = (
            [t.strip() for t in instance.audience_tags.split(",")]
            if instance.audience_tags else []
        )

        return rep

    #  Validation
    def validate_subgenres(self, value):
        if value and len(value) > 3:
            raise serializers.ValidationError("Maximum 3 subgenres allowed.")
        
        # Get primary genre from the data
        primary_genre = self.initial_data.get('primary_genre')
        if primary_genre:
            # Get valid subgenres for the selected primary genre
            valid_subgenres = dict(GENRE_SUBGENRE_MAPPING.get(primary_genre, [])).keys()
            invalid = [v for v in value if v not in valid_subgenres]
            
            if invalid:
                raise serializers.ValidationError(
                    f"Invalid subgenres for {primary_genre}: {', '.join(invalid)}. "
                    f"Valid subgenres for {primary_genre} are: {', '.join(valid_subgenres)}"
                )
        else:
            # If no primary genre selected, validate against all subgenres
            valid_subgenres = dict(ALL_SUBGENRES).keys()
            invalid = [v for v in value if v not in valid_subgenres]
            
            if invalid:
                raise serializers.ValidationError(
                    f"Invalid subgenres: {', '.join(invalid)}"
                )

        return value

    def validate_audience_tags(self, value):
        valid_tags = dict(AUDIENCE_TAG_CHOICES).keys()
        invalid = [v for v in value if v not in valid_tags]

        if invalid:
            raise serializers.ValidationError(
                f"Invalid audience tags: {', '.join(invalid)}"
            )

        return value

    #  Save lists as comma-separated strings
    def update(self, instance, validated_data):
        subgenres = validated_data.pop("subgenres", None)
        audience_tags = validated_data.pop("audience_tags", None)

        if subgenres is not None:
            instance.subgenres = ",".join(subgenres)

        if audience_tags is not None:
            instance.audience_tags = ",".join(audience_tags)

        return super().update(instance, validated_data)
    pen_name = serializers.CharField(required=True, allow_blank=False)
    author_bio = serializers.CharField(required=True, allow_blank=False)
    profile_photo = serializers.ImageField(required=True, allow_null=False)
    
    # Step 1: User selects what they want to provide
    genre_preferences = serializers.ChoiceField(
        choices=PRIMARY_GENRE_CHOICES,
        required=True,
        help_text="Select what you want to provide: Primary Genre, Subgenres, or Audience/Tone Tags"
    )
    
    # Step 2: Fields based on selection
    primary_genre = serializers.ChoiceField(
        choices=PRIMARY_GENRE_CHOICES,
        required=False,
        help_text="Primary Genre - required if Primary Genre selected"
    )
    subgenres = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        max_length=3,
        help_text="Subgenres - required if Subgenres selected, maximum of 3"
    )
    audience_tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="Audience/Tone Tags - required if Audience/Tone Tags selected"
    )

    class Meta:
        model = UserProfile
        fields = ['pen_name', 'author_bio', 'profile_photo', 'genre_preferences', 'primary_genre', 'subgenres', 'audience_tags']

    def validate(self, data):
        primary_genre = data.get('primary_genre')
        subgenres_list = data.get('subgenres', [])

        if primary_genre and subgenres_list:
            # 1. Look up the allowed subgenres for the selected primary genre
            # This pulls from your ROMANCE_SUBGENRES, MYSTERY_SUBGENRES, etc.
            allowed_tuples = GENRE_SUBGENRE_MAPPING.get(primary_genre, [])
            allowed_keys = [item[0] for item in allowed_tuples]

            # 2. Check each selected subgenre against the allowed list
            for sub in subgenres_list:
                if sub not in allowed_keys:
                    raise serializers.ValidationError({
                        "subgenres": f"'{sub}' is not a valid subgenre for the '{primary_genre}' category."
                    })

        return data

    def get_subgenres_display(self, obj):
        # Returns readable labels instead of keys for the UI
        all_subs_dict = dict(ALL_SUBGENRES)
        return [all_subs_dict.get(s.strip()) for s in obj.get_subgenres_list()] 
    
    def to_internal_value(self, data):
        # Converts the incoming JSON list back to a comma-separated string for the DB
        if 'subgenres' in data and isinstance(data['subgenres'], list):
            data['subgenres'] = ",".join(data['subgenres'])
        return super().to_internal_value(data)

    def to_representation(self, instance):
        # Convert the string from the DB back into a list for the frontend JSON
        repr = super().to_representation(instance)
        if instance.subgenres:
            repr['subgenres'] = instance.subgenres.split(',')
        else:
            repr['subgenres'] = []
        return repr

    def validate(self, data):
        """Validate that required fields are provided based on genre_preferences selection"""
        genre_pref = data.get('genre_preferences')
        
        if genre_pref == 'primary':
            if not data.get('primary_genre'):
                raise serializers.ValidationError({
                    'primary_genre': 'Primary Genre is required when Primary Genre is selected.'
                })
            # Clear other fields
            data['subgenres'] = []
            data['audience_tags'] = []
            
        elif genre_pref == 'subgenre':
            if not data.get('subgenres'):
                raise serializers.ValidationError({
                    'subgenres': 'At least one subgenre is required when Subgenres is selected.'
                })
            # Clear other fields
            data['primary_genre'] = None
            data['audience_tags'] = []
            
        elif genre_pref == 'tone':
            if not data.get('audience_tags'):
                raise serializers.ValidationError({
                    'audience_tags': 'At least one audience tag is required when Audience/Tone Tags is selected.'
                })
            # Clear other fields
            data['primary_genre'] = None
            data['subgenres'] = []
        
        return data

    def validate_subgenres(self, value):
        """Validate subgenres - max 3, check against valid choices"""
        if value and len(value) > 3:
            raise serializers.ValidationError("Maximum of 3 subgenres allowed.")
        
        # Get valid subgenre values
        valid_subgenres = dict(ALL_SUBGENRES).keys()
        
        if value:
            invalid = [s for s in value if s not in valid_subgenres]
            if invalid:
                raise serializers.ValidationError(
                    f"Invalid subgenres: {', '.join(invalid)}. Must be from valid subgenre list."
                )
        
        return value

    def validate_audience_tags(self, value):
        """Validate audience tags against valid choices"""
        valid_tags = dict(AUDIENCE_TAGS_CHOICES).keys()
        
        if value:
            invalid = [t for t in value if t not in valid_tags]
            if invalid:
                raise serializers.ValidationError(
                    f"Invalid audience tags: {', '.join(invalid)}. Must be from valid audience tags list."
                )
        
        return value

    def update(self, instance, validated_data):
        """Save lists as comma-separated strings"""
        # Convert subgenres list to comma-separated string
        if 'subgenres' in validated_data:
            subgenres = validated_data.pop('subgenres')
            instance.subgenres = ','.join(subgenres) if subgenres else None
        
        # Convert audience_tags list to comma-separated string
        if 'audience_tags' in validated_data:
            audience_tags = validated_data.pop('audience_tags')
            instance.audience_tags = ','.join(audience_tags) if audience_tags else None
        
        return super().update(instance, validated_data)


class OnlinePresenceSerializer(serializers.ModelSerializer):
    website_url = serializers.URLField(required=True)
    collaboration_status = serializers.ChoiceField(choices=COLLABORATION_STATUS, required=True)

    class Meta:
        model = UserProfile
        fields = ['website_url', 'facebook_url', 'instagram_url', 'tiktok_url', 'collaboration_status']


class UserProfileReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    # Convert comma-separated strings to lists for display
    subgenres = serializers.SerializerMethodField()
    audience_tags = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'user_email', 'user_username', 'pen_name', 'author_bio', 
            'primary_genre', 'subgenres', 'audience_tags', 'profile_photo', 
            'website_url', 'facebook_url', 'instagram_url', 'tiktok_url', 
            'collaboration_status', 'created_at', 'updated_at'
        ]
    
    def get_subgenres(self, obj):
        if obj.subgenres:
            return [s.strip() for s in obj.subgenres.split(',') if s.strip()]
        return []
    
    def get_audience_tags(self, obj):
        if obj.audience_tags:
            return [t.strip() for t in obj.audience_tags.split(',') if t.strip()]
        return []
