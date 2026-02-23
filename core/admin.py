from django.contrib import admin
from .models import Profile, NewsletterSlot, Notification, SwapRequest, Book
# Register your models here.
admin.site.register(Profile)
admin.site.register(NewsletterSlot)
admin.site.register(Notification)
admin.site.register(SwapRequest)
admin.site.register(Book)