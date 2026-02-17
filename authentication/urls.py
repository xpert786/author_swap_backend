from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginAPIView, SignupAPIView, ForgotPasswordAPIView, ResetPasswordAPIView, AccountBasicsAPIView, OnlinePresenceAPIView, UserProfileReviewAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('signup/', SignupAPIView.as_view(), name='signup'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset-password'),
    path('onboarding/account-basics/', AccountBasicsAPIView.as_view(), name='account-basics'),
    path('onboarding/online-presence/', OnlinePresenceAPIView.as_view(), name='online-presence'),
    path('profile/review/', UserProfileReviewAPIView.as_view(), name='profile-review'),
]