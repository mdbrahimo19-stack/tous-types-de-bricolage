from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LogoutView,
    MeBecomeProviderView,
    MeDeleteView,
    MeExportView,
    MePhotoView,
    MePrivacyView,
    MeView,
    OTPRequestView,
    OTPVerifyView,
)

app_name = "accounts"

urlpatterns = [
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("me/photo/", MePhotoView.as_view(), name="me-photo"),
    path("me/privacy/", MePrivacyView.as_view(), name="me-privacy"),
    path("me/export/", MeExportView.as_view(), name="me-export"),
    path("me/become-provider/", MeBecomeProviderView.as_view(), name="me-become-provider"),
    path("me/delete/", MeDeleteView.as_view(), name="me-delete"),
]
