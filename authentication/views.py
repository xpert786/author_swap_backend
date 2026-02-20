from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .serializers import LoginSerializer, SignupSerializer, ForgotPasswordSerializer, ResetPasswordSerializer, AccountBasicsSerializer, OnlinePresenceSerializer, UserProfileReviewSerializer
from .models import PasswordResetToken, UserProfile, PRIMARY_GENRE_CHOICES, GENRE_SUBGENRE_MAPPING, AUDIENCE_TAG_CHOICES

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

