from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginAPIView, SignupAPIView, ForgotPasswordAPIView, VerifyOTPAPIView, ResetPasswordAPIView,
    AccountBasicsAPIView, OnlinePresenceAPIView, UserProfileReviewAPIView,
    SubgenresByGenreAPIView, GenreChoicesAPIView, PrimaryGenreChoicesView,
    AllSubgenresView, AudienceTagsView
)

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('signup/', SignupAPIView.as_view(), name='signup'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('verify-otp/', VerifyOTPAPIView.as_view(), name='verify-otp'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset-password'),
    path('onboarding/account-basics/', AccountBasicsAPIView.as_view(), name='account-basics'),
    path('onboarding/online-presence/', OnlinePresenceAPIView.as_view(), name='online-presence'),
    path('profile/review/', UserProfileReviewAPIView.as_view(), name='profile-review'),
    path('subgenres-by-genre/', SubgenresByGenreAPIView.as_view(), name='subgenres-by-genre'),
    path('genre-choices/', GenreChoicesAPIView.as_view(), name='genre-choices'),
    path('primary-genres/', PrimaryGenreChoicesView.as_view(), name='primary-genres'),
    path('all-subgenres/', AllSubgenresView.as_view(), name='all-subgenres'),
    path('audience-tags/', AudienceTagsView.as_view(), name='audience-tags'),
]       