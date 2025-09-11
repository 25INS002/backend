from django.urls import path
from .views import (
    SignupView,
    VerifyOTPView,
    LoginView,
    LogoutView,
    RequestPasswordResetOTPView,
    ResetPasswordView,
    UserDetailView,
    ResendSignupOTPView,
    ResendPasswordResetOTPView,
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", UserDetailView.as_view(), name="me"), 
    # Password reset
    path(
        "request-reset-otp/",
        RequestPasswordResetOTPView.as_view(),
        name="request-reset-otp",
    ),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("resend-signup-otp/", ResendSignupOTPView.as_view(), name="resend-signup-otp"),
    path(
        "resend-reset-otp/",
        ResendPasswordResetOTPView.as_view(),
        name="resend-reset-otp",
    ),
]
