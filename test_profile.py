import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "author_swap.settings")
django.setup()

from core.models import Profile, User
from core.serializers import ProfileSerializer

user = User.objects.first()
profile = Profile.objects.get_or_create(user=user)[0]
serializer = ProfileSerializer(profile)
print(serializer.data)
