from django.urls import path
from .views import (
    SignupView,
    VerifyOTPView,
    LoginView,
    LogoutView,
    RequestPasswordResetOTPView,
    ResetPasswordView,
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Password reset
    path(
        "request-reset-otp/",
        RequestPasswordResetOTPView.as_view(),
        name="request-reset-otp",
    ),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]
