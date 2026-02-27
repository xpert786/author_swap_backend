from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .serializers import LoginSerializer, SignupSerializer, ForgotPasswordSerializer, VerifyOTPSerializer, ResetPasswordSerializer, AccountBasicsSerializer, OnlinePresenceSerializer, UserProfileReviewSerializer, EditPenNameSerializer
from .models import PasswordResetToken, UserProfile, PRIMARY_GENRE_CHOICES, GENRE_SUBGENRE_MAPPING, AUDIENCE_TAG_CHOICES
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ImportError:
    id_token = None
    google_requests = None


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
                'message': 'Password reset OTP sent to your email.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPAPIView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            # Store the user's email in the session for the reset-password step
            reset_token = serializer.validated_data['reset_token']
            request.session['reset_email'] = reset_token.user.email
            return Response({
                'message': 'OTP verified successfully.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordAPIView(APIView):
    def post(self, request):
        # Get the email stored in the session during verify-otp
        reset_email = request.session.get('reset_email')
        if not reset_email:
            return Response(
                {"detail": "Session expired. Please verify your OTP again."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Inject email into the data so the serializer can find the user
        data = request.data.copy()
        data['email'] = reset_email

        serializer = ResetPasswordSerializer(data=data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            reset_token = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']
            
            user.set_password(new_password)
            user.save()
            
            reset_token.is_used = True
            reset_token.save()

            # Clean up the session
            request.session.pop('reset_email', None)
            
            return Response({
                'message': 'Password reset successfully.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountBasicsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
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
        profile, created = UserProfile.objects.get_or_create(user=request.user)
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
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileReviewSerializer(profile)
        return Response({
            'message': 'User profile retrieved successfully.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
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
        # Prepare subgenres mapping for API response
        subgenres_by_genre = {}
        for genre_key, subgenre_list in GENRE_SUBGENRE_MAPPING.items():
            # Get the display label for the primary genre
            genre_label = dict(PRIMARY_GENRE_CHOICES).get(genre_key, genre_key)
            
            subgenres_by_genre[genre_label] = [
                {'value': val, 'label': label} 
                for val, label in subgenre_list
            ]
        
        return Response({
            'primary_genres': [{'value': v, 'label': l} for v, l in PRIMARY_GENRE_CHOICES],
            'subgenres': subgenres_by_genre,
            'audience_tags': [{'value': v, 'label': l} for v, l in AUDIENCE_TAG_CHOICES],
            'rules': {
                'primary_genre_required': True,
                'subgenres_max': 3,
                'subgenres_optional': True,
                'audience_tags_optional': True,
                'matching_priority': ['Primary Genre', 'Subgenre overlap', 'Audience / Tone tags']
            }
        }, status=status.HTTP_200_OK)


class PrimaryGenreChoicesView(APIView):
    """
    Returns the list of primary genres.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = [
            {"value": key, "label": label}
            for key, label in PRIMARY_GENRE_CHOICES
        ]
        return Response(data, status=status.HTTP_200_OK)


class AllSubgenresView(APIView):
    """
    Returns all subgenres grouped by their primary genre.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {}
        for primary_genre, subgenres in GENRE_SUBGENRE_MAPPING.items():
            data[primary_genre] = [
                {"value": val, "label": label}
                for val, label in subgenres
            ]
        return Response(data, status=status.HTTP_200_OK)


class AudienceTagsView(APIView):
    """
    Returns the list of audience tags.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = [
            {"value": val, "label": label}
            for val, label in AUDIENCE_TAG_CHOICES
        ]
        return Response(data, status=status.HTTP_200_OK)


class EditPenNameAPIView(APIView):
    """
    API endpoint to quickly update just the pen_name of the authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = EditPenNameSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Pen name updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleOAuthView(APIView):
    """
    POST /api/auth/google/
    
    Accepts a Google ID token from the frontend (obtained after the user
    completes Google Sign-In on the client side).
    
    Flow:
    1. Frontend sends { "id_token": "<google_id_token>" }
    2. Backend verifies token with Google's public keys
    3. If user exists → log in and return JWT
    4. If user doesn't exist → create account and return JWT
    
    Frontend Integration:
    - Use Google Sign-In SDK / Google One Tap
    - On success, send the id_token to this endpoint
    """

    def post(self, request):
        id_token_str = request.data.get('id_token')
        if not id_token_str:
            return Response(
                {"error": "id_token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if id_token is None:
            return Response(
                {"error": "Google authentication library not installed on the server. Please run 'pip install google-auth requests'"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Verify the Google ID token
        try:
            google_client_id = settings.GOOGLE_OAUTH_CLIENT_ID
            id_info = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                google_client_id
            )
        except ValueError as e:
            return Response(
                {"error": f"Invalid Google token: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {"error": f"Token verification failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract user info from verified token
        email = id_info.get('email')
        first_name = id_info.get('given_name', '')
        last_name = id_info.get('family_name', '')
        google_user_id = id_info.get('sub')  # Unique Google user ID
        picture = id_info.get('picture', '')

        if not email:
            return Response(
                {"error": "Could not retrieve email from Google account."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create the user
        user, is_new_user = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': first_name,
                'last_name': last_name,
            }
        )

        # If username already taken, make it unique
        if is_new_user:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                username = f"{base_username}{counter}"
                counter += 1
            if user.username != username:
                user.username = username
                user.save()

        # Store Google ID in profile if available
        if hasattr(user, 'profile'):
            profile = user.profile
            if picture and not profile.profile_photo:
                # Store google picture URL if no photo yet (optional)
                profile.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        return Response({
            'refresh': str(refresh),
            'access': str(access_token),
            'token': str(access_token),
            'is_new_user': is_new_user,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }, status=status.HTTP_200_OK if not is_new_user else status.HTTP_201_CREATED)
