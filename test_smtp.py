import os
import sys
import django
sys.path.append('/home/ariyan/Ariyan/author_swap_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'author_swap.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings
import traceback

print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")

try:
    print("Sending test email...")
    send_mail(
        subject="Test Author Swap Email",
        message="This is a test email from the Author Swap application.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['ariyanrana3434@gmail.com'],
        fail_silently=False,
    )
    print("Test email sent successfully!")
except Exception as e:
    print(f"Failed to send email. Error: {e}")
    traceback.print_exc()
