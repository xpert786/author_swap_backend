import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "author_swap.settings")
django.setup()

from core.models import Profile
from authentication.models import UserProfile

count = 0
for u_prof in UserProfile.objects.all():
    if u_prof.pen_name:
        core_prof = Profile.objects.filter(user=u_prof.user).first()
        if core_prof and not core_prof.pen_name:
            core_prof.pen_name = u_prof.pen_name
            core_prof.save()
            count += 1
print(f"Updated {count} profiles.")
