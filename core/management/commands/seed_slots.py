from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Profile, NewsletterSlot, SwapRequest, Book
from authentication.constants import PRIMARY_GENRE_CHOICES
import random
from datetime import timedelta, date, time

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with test NewsletterSlots and related data so /api/slots/explore/ is populated.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")

        # 1. Create a few fake users with profiles
        genres_list = [choice[0] for choice in PRIMARY_GENRE_CHOICES]
        fake_users_data = [
            {"username": "alice_author", "email": "alice@example.com", "name": "Alice Johnson"},
            {"username": "bob_writer", "email": "bob@example.com", "name": "Bob Writer"},
            {"username": "charlie_books", "email": "charlie@example.com", "name": "Charlie Chaplin"},
            {"username": "david_novels", "email": "david@example.com", "name": "David Smith"},
        ]
        
        users = []
        for udata in fake_users_data:
            user, created = User.objects.get_or_create(username=udata['username'], defaults={'email': udata['email']})
            if created:
                user.set_password('password123')
                user.save()
            users.append((user, udata['name']))

            # Create or update profile
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.name = udata['name']
            profile.primary_genre = random.choice(genres_list) if genres_list else "Fantasy"
            profile.reputation_score = round(random.uniform(4.0, 5.0), 1)
            profile.avg_open_rate = round(random.uniform(30.0, 50.0), 1)
            profile.avg_click_rate = round(random.uniform(5.0, 15.0), 1)
            profile.monthly_growth = random.randint(100, 500)
            profile.send_reliability_percent = round(random.uniform(90.0, 100.0), 1)
            profile.confirmed_sends_score = random.randint(30, 50)
            profile.timeliness_score = random.randint(20, 30)
            profile.missed_sends_penalty = random.randint(0, 10)
            profile.communication_score = random.randint(20, 30)
            profile.save()

        # 2. Create Newsletter Slots for each user
        today = date.today()
        created_slots = []
        for user, _ in users:
            # Each user gets 2 slots
            for i in range(2):
                slot_date = today + timedelta(days=random.randint(1, 30))
                slot_time = time(random.randint(8, 18), 0)
                genre = random.choice(genres_list) if genres_list else "Science Fiction"
                
                slot = NewsletterSlot.objects.create(
                    user=user,
                    send_date=slot_date,
                    send_time=slot_time,
                    status='available',
                    audience_size=random.randint(1000, 50000),
                    preferred_genre=genre,
                    max_partners=random.randint(3, 8),
                    visibility='public'
                )
                created_slots.append(slot)

        # 3. Simulate Swap Partners for a realistic UI
        # We'll create random SwapRequests marked as 'confirmed' to simulate existing partners in these slots
        for slot in created_slots:
            num_partners = random.randint(0, 2)
            # Pick random users who are NOT the slot owner to act as partners
            potential_partners = [u for u, _ in users if u != slot.user]
            random.shuffle(potential_partners)
            
            for i in range(num_partners):
                if i < len(potential_partners):
                    partner_user = potential_partners[i]
                    SwapRequest.objects.create(
                        slot=slot,
                        requester=partner_user,
                        status=random.choice(['confirmed', 'verified'])
                    )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(users)} users, {len(created_slots)} public newsletter slots, and random swap partners!'))
        self.stdout.write(self.style.SUCCESS('You can now hit /api/slots/explore/ and see data!'))
