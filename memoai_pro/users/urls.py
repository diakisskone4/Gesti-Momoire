# users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, ProfileView, LogoutView,
    Request2FAView, Verify2FAView, ChangePasswordView,
    GoogleOAuthView, DeleteAccountView,
    UserDirectoryView, AdminUserViewSet, AdminStatsView, ThrottledTokenRefreshView,
)

from .password_reset import PasswordResetConfirmView, PasswordResetRequestView

admin_router = DefaultRouter()
admin_router.register(r'users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('refresh/', ThrottledTokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('2fa/request/', Request2FAView.as_view(), name='request_2fa'),
    path('2fa/verify/', Verify2FAView.as_view(), name='verify_2fa'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('google/', GoogleOAuthView.as_view(), name='google_oauth'),
    path('delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('directory/', UserDirectoryView.as_view(), name='user_directory'),
    path('admin/stats/', AdminStatsView.as_view(), name='admin_stats'),
    path('admin/', include(admin_router.urls)),
]