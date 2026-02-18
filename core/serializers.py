from rest_framework import serializers
from .models import NewsletterSlot
from authentication.models import GENRE_SUBGENRE_MAPPING
from .models import Book

class NewsletterSlotSerializer(serializers.ModelSerializer):
    subgenres = serializers.ListField(
        child=serializers.CharField(), 
        required=False,
        allow_empty=True
    )

    class Meta:
        model = NewsletterSlot
        fields = '__all__'
        read_only_fields = ['user']
        extra_kwargs = {
            'audience_size': {'required': True},
            'max_partners': {'required': True},
            'visibility': {'required': True},
        }

    def validate(self, data):
        genre = data.get('preferred_genre')
        subs = data.get('subgenres', [])
        
        # Audience size custom validation if needed (e.g., must be > 0)
        # but required=True is handled by extra_kwargs/framework

        if genre and subs:
             allowed_sub_tuples = GENRE_SUBGENRE_MAPPING.get(genre, [])
             allowed_keys = [item[0] for item in allowed_sub_tuples]

             for sub in subs:
                if sub not in allowed_keys:
                    raise serializers.ValidationError({
                        "subgenres": f"'{sub}' is not a valid subgenre for {genre}. "
                                     f"Please only select from the {genre} list."
                    })
        return data

    def to_internal_value(self, data):
        data = data.copy()
        if 'subgenres' in data and isinstance(data['subgenres'], list):
            data['subgenres'] = ",".join(data['subgenres'])
        return super().to_internal_value(data)

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        if instance.subgenres:
            repr['subgenres'] = instance.subgenres.split(',')
        else:
            repr['subgenres'] = []
        return repr

class BookSerializer(serializers.ModelSerializer):
    # Allows the frontend to send an array of subgenres
    subgenres = serializers.ListField(child=serializers.CharField(), required=True)

    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ['user']
        extra_kwargs = {
            'price_tier': {'required': True},
            'amazon_url': {'required': True},
            'apple_url': {'required': True},
            'kobo_url': {'required': True},
            'barnes_noble_url': {'required': True},
        }

    def validate(self, data):
        genre = data.get('primary_genre')
        subs = data.get('subgenres', [])

        if genre and subs:
            # 1. Fetch the allowed subgenres for the selected category
            allowed_tuples = GENRE_SUBGENRE_MAPPING.get(genre, [])
            allowed_keys = [item[0] for item in allowed_tuples]

            # 2. Enforce the match
            for s in subs:
                if s not in allowed_keys:
                    raise serializers.ValidationError({
                        "subgenres": f"'{s}' is not a valid subgenre for the {genre} category."
                    })
        return data

    def to_internal_value(self, data):
        data = data.copy()  # Make a mutable copy
        # Flatten the list back to a string for the DB CharField
        if 'subgenres' in data and isinstance(data['subgenres'], list):
            data['subgenres'] = ",".join(data['subgenres'])
        return super().to_internal_value(data)

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        if instance.subgenres:
            # If it's already a list (from validated_data), use it
            if isinstance(instance.subgenres, list):
                repr['subgenres'] = instance.subgenres
            # If it's a string (from DB), split it
            elif isinstance(instance.subgenres, str):
                repr['subgenres'] = instance.subgenres.split(',')
        else:
            repr['subgenres'] = []
        return repr