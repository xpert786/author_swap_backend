from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from core.models import Notification

User = get_user_model()

class Command(BaseCommand):
    help = 'Send a notification to a user by their email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user to notify')
        parser.add_argument('message', type=str, help='Notification message')
        parser.add_argument('--title', type=str, default='System Notification', help='Notification title')
        parser.add_argument('--badge', type=str, default='NEW', help='Notification badge (SWAP, VERIFIED, REMINDER, DEADLINE, NEW)')

    def handle(self, *args, **options):
        email = options['email']
        message = options['message']
        title = options['title']
        badge = options['badge']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Try to find by username if email doesn't work, just in case
            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                raise CommandError(f'User with email or username "{email}" does not exist')

        notification = Notification.objects.create(
            recipient=user,
            title=title,
            message=message,
            badge=badge
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully sent notification to {user.username}: "{message}"')
        )
