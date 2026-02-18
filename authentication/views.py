from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .serializers import LoginSerializer, SignupSerializer, ForgotPasswordSerializer, ResetPasswordSerializer, AccountBasicsSerializer, OnlinePresenceSerializer, UserProfileReviewSerializer
from .models import PasswordResetToken, PRIMARY_GENRE_CHOICES, GENRE_SUBGENRE_MAPPING, AUDIENCE_TAG_CHOICES

User = get_user_model()


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'refresh': str(refresh),
                'access': str(access_token),
                'token': str(access_token),  # For backward compatibility
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignupAPIView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'refresh': str(refresh),
                'access': str(access_token),
                'token': str(access_token),  # For backward compatibility
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordAPIView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            reset_token = PasswordResetToken(user=user)
            otp = reset_token.generate_otp()
            reset_token.save()
            
            send_mail(
                subject='Password Reset OTP',
                message=f'Your password reset OTP is: {otp}\n\nThis OTP will expire in 10 minutes.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
            
            return Response({
                'message': 'Password reset OTP sent to your email.',
                'otp': otp
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            reset_token = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']
            
            user.set_password(new_password)
            user.save()
            
            reset_token.is_used = True
            reset_token.save()
            
            return Response({
                'message': 'Password reset successfully.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountBasicsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        serializer = AccountBasicsSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Account basics saved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OnlinePresenceAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = request.user.profile
        serializer = OnlinePresenceSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Online presence saved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileReviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileReviewSerializer(profile)
        return Response({
            'message': 'User profile retrieved successfully.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request):
        profile = request.user.profile
        serializer = UserProfileReviewSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'User profile updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)


class SubgenresByGenreAPIView(APIView):
    """Get subgenres based on selected primary genre"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        primary_genre = request.GET.get('primary_genre')
        
        if not primary_genre:
            return Response({
                'error': 'primary_genre parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get subgenres for the selected primary genre
        subgenres = GENRE_SUBGENRE_MAPPING.get(primary_genre, [])
        
        return Response({
            'primary_genre': primary_genre,
            'subgenres': subgenres
        }, status=status.HTTP_200_OK)


class GenreChoicesAPIView(APIView):
    """API to return all valid genre, subgenre, and audience tag choices"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Group subgenres by primary genre for better organization
        subgenres_by_genre = {
            'Romance': [
                {'value': v, 'label': l} for v, l in [
                    ('contemporary_romance', 'Contemporary Romance'),
                    ('romantic_comedy', 'Romantic Comedy'),
                    ('small_town_romance', 'Small Town Romance'),
                    ('sports_romance', 'Sports Romance'),
                    ('billionaire_romance', 'Billionaire Romance'),
                    ('bad_boy_romance', 'Bad Boy Romance'),
                    ('new_adult_romance', 'New Adult Romance'),
                    ('erotic_romance', 'Erotic Romance / Erotica'),
                    ('reverse_harem', 'Reverse Harem / Why Choose Romance'),
                    ('paranormal_romance', 'Paranormal Romance'),
                    ('romantic_suspense', 'Romantic Suspense'),
                    ('dark_romance', 'Dark Romance'),
                    ('historical_romance', 'Historical Romance'),
                    ('western_romance', 'Western Romance'),
                    ('military_romance', 'Military Romance'),
                    ('medical_romance', 'Medical Romance'),
                    ('holiday_romance', 'Holiday Romance'),
                    ('sci_fi_romance', 'Sci-Fi Romance'),
                    ('fantasy_romance', 'Fantasy Romance'),
                    ('lgbtq_romance', 'LGBTQ+ Romance'),
                ]
            ],
            'Mystery / Thriller': [
                {'value': v, 'label': l} for v, l in [
                    ('cozy_mystery', 'Cozy Mystery'),
                    ('amateur_sleuth', 'Amateur Sleuth'),
                    ('police_procedural', 'Police Procedural'),
                    ('crime_thriller', 'Crime Thriller'),
                    ('psychological_thriller', 'Psychological Thriller'),
                    ('legal_thriller', 'Legal Thriller'),
                    ('techno_thriller', 'Techno-Thriller'),
                    ('suspense', 'Suspense'),
                    ('historical_mystery', 'Historical Mystery'),
                ]
            ],
            'Science Fiction': [
                {'value': v, 'label': l} for v, l in [
                    ('space_opera', 'Space Opera'),
                    ('military_sci_fi', 'Military Sci-Fi'),
                    ('dystopian', 'Dystopian'),
                    ('post_apocalyptic', 'Post-Apocalyptic'),
                    ('time_travel', 'Time Travel'),
                    ('hard_sci_fi', 'Hard Sci-Fi'),
                    ('alien_first_contact', 'Alien / First Contact'),
                    ('cyberpunk', 'Cyberpunk'),
                ]
            ],
            'Fantasy': [
                {'value': v, 'label': l} for v, l in [
                    ('epic_high_fantasy', 'Epic / High Fantasy'),
                    ('urban_fantasy', 'Urban Fantasy'),
                    ('dark_fantasy', 'Dark Fantasy'),
                    ('portal_fantasy', 'Portal Fantasy'),
                    ('sword_sorcery', 'Sword & Sorcery'),
                    ('mythology_retellings', 'Mythology / Retellings'),
                    ('litrpg_gamelit', 'LitRPG / GameLit'),
                ]
            ],
            'Young Adult (YA)': [
                {'value': v, 'label': l} for v, l in [
                    ('ya_romance', 'YA Romance'),
                    ('ya_fantasy', 'YA Fantasy'),
                    ('ya_sci_fi', 'YA Sci-Fi'),
                    ('ya_contemporary', 'YA Contemporary'),
                    ('ya_mystery_thriller', 'YA Mystery / Thriller'),
                    ('ya_paranormal', 'YA Paranormal'),
                ]
            ],
            "Children's Books": [
                {'value': v, 'label': l} for v, l in [
                    ('picture_books', 'Picture Books'),
                    ('early_readers', 'Early Readers'),
                    ('chapter_books', 'Chapter Books'),
                    ('middle_grade', 'Middle Grade'),
                    ('educational', 'Educational'),
                    ('comics_graphic_novels', 'Comics & Graphic Novels'),
                ]
            ],
            'Horror': [
                {'value': v, 'label': l} for v, l in [
                    ('psychological_horror', 'Psychological Horror'),
                    ('supernatural_horror', 'Supernatural Horror'),
                    ('paranormal_horror', 'Paranormal Horror'),
                    ('dark_fantasy_horror', 'Dark Fantasy Horror'),
                    ('thriller_horror', 'Thriller Horror'),
                ]
            ],
            'Literary Fiction': [
                {'value': v, 'label': l} for v, l in [
                    ('contemporary_literary', 'Contemporary Literary'),
                    ('historical_literary', 'Historical Literary'),
                    ('experimental', 'Experimental'),
                ]
            ],
            "Women's Fiction": [
                {'value': v, 'label': l} for v, l in [
                    ('contemporary_womens', "Contemporary Women's Fiction"),
                    ('book_club_fiction', 'Book Club Fiction'),
                    ('family_relationships', 'Family / Relationships'),
                    ('emotional_dramatic', 'Emotional / Dramatic'),
                ]
            ],
            'Nonfiction': [
                {'value': v, 'label': l} for v, l in [
                    ('memoir_biography', 'Memoir / Biography'),
                    ('self_help', 'Self-Help / Personal Development'),
                    ('business_finance', 'Business / Finance'),
                    ('health_wellness', 'Health & Wellness'),
                    ('parenting_family', 'Parenting / Family'),
                    ('faith_spirituality', 'Faith / Spirituality'),
                    ('education', 'Education'),
                    ('writing_publishing', 'Writing / Publishing'),
                ]
            ],
            'Action / Adventure': [
                {'value': v, 'label': l} for v, l in [
                    ('military_war', 'Military / War'),
                    ('espionage', 'Espionage'),
                    ('survival', 'Survival'),
                    ('adventure_thriller', 'Adventure Thriller'),
                ]
            ],
            'Comics & Graphic Novels': [
                {'value': v, 'label': l} for v, l in [
                    ('fiction', 'Fiction'),
                    ('nonfiction', 'Nonfiction'),
                    ('childrens', "Children's"),
                    ('manga', 'Manga'),
                ]
            ],
        }
        
        return Response({
            'primary_genres': [{'value': v, 'label': l} for v, l in PRIMARY_GENRE_CHOICES],
            'subgenres': subgenres_by_genre,
            'audience_tags': [{'value': v, 'label': l} for v, l in AUDIENCE_TAGS_CHOICES],
            'rules': {
                'primary_genre_required': True,
                'subgenres_max': 3,
                'subgenres_optional': True,
                'audience_tags_optional': True,
                'matching_priority': ['Primary Genre', 'Subgenre overlap', 'Audience / Tone tags']
            }
        }, status=status.HTTP_200_OK)
