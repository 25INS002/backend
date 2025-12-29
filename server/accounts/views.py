from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
import random, datetime
from django.contrib.auth.hashers import make_password
from utils.util import send_otp_email

# For demo: In-memory OTP store → replace with Redis/DB in production
otp_store = {}  # { "username": { "otp": "123456", "expires_at": datetime } }
reset_otp_store = {}


# --- SIGNUP ---
class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")

        if not username or not email or not password or not first_name or not last_name:
            return Response(
                {"error": "All fields required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "Email already registered"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create inactive user (will be activated after OTP verification)
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False,
            first_name=first_name,
            last_name=last_name,
        )

        # Generate OTP
        otp = send_otp_email(email, reason="signup")
        otp_store[username] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production: send OTP via email/SMS
        return Response(
            {
                "message": "User created. Verify OTP to activate.",
                "username": user.username,
            },
            status=status.HTTP_201_CREATED,
        )


# --- RESEND SIGNUP OTP ---
class ResendSignupOTPView(APIView):
    def post(self, request):
        username = request.data.get("username")
        if not username:
            return Response(
                {"error": "Username required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)
            if user.is_active:
                return Response(
                    {"error": "User already verified"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate new OTP
        otp = send_otp_email(user.email, reason="signup")
        otp_store[username] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production → send OTP via email/SMS
        return Response({"message": "OTP resent"}, status=status.HTTP_200_OK)


# --- VERIFY OTP FOR SIGNUP ---
class VerifyOTPView(APIView):
    def post(self, request):
        username = request.data.get("username")
        otp = request.data.get("otp")

        if not username or not otp:
            return Response(
                {"error": "Username and OTP required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if username not in otp_store:
            return Response(
                {"error": "No OTP found. Request again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = otp_store[username]
        if datetime.datetime.now() > record["expires_at"]:
            del otp_store[username]
            return Response(
                {"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST
            )

        if record["otp"] != otp:
            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)
            user.is_active = True
            user.save()
            del otp_store[username]
            return Response(
                {"message": "Account verified. You can now log in."},
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


# --- LOGIN (Email + Password, sets cookies) ---
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(username=user_obj.username, password=password)
        if user is None or not user.is_active:
            return Response(
                {"error": "Invalid credentials or inactive account"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),  # optional
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_200_OK,
        )


# --- LOGOUT (Clears cookies) ---
class LogoutView(APIView):
    def post(self, request):
        return Response({"message": "Logged out"})



# --- REQUEST RESET OTP ---
class RequestPasswordResetOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        otp = send_otp_email(email, reason="forgotpassword")
        reset_otp_store[email] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production → send OTP via email/SMS, not in response
        return Response({"message": "OTP sent to email"}, status=status.HTTP_200_OK)


# --- RESEND RESET PASSWORD OTP ---
class ResendPasswordResetOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate new OTP
        otp = send_otp_email(email, reason="forgotpassword")
        reset_otp_store[email] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production → send OTP via email/SMS
        return Response({"message": "Reset OTP resent"}, status=status.HTTP_200_OK)


# --- VERIFY OTP & RESET PASSWORD ---
class ResetPasswordView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not email or not otp or not new_password:
            return Response(
                {"error": "Email, OTP and new password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if email not in reset_otp_store:
            return Response(
                {"error": "No OTP found. Request again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = reset_otp_store[email]
        if datetime.datetime.now() > record["expires_at"]:
            del reset_otp_store[email]
            return Response(
                {"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST
            )

        if record["otp"] != otp:
            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()
            del reset_otp_store[email]
            return Response(
                {"message": "Password reset successful"}, status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


# --- GET LOGGED IN USER INFO ---
class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_joined": user.date_joined,
                "is_staff": user.is_staff,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "last_login": user.last_login,
            }
        )

# --- UPDATE USER PROFILE ---
class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        data = request.data

        updatable_fields = ["first_name", "last_name", "email"]

        new_email = data.get("email")
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                return Response(
                    {"error": "Email already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])

        user.save()

        return Response(
            {
                "message": "Profile updated successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            }
        )

# --- REFRESH TOKEN ---
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Refresh token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh = RefreshToken(refresh_token)
            return Response(
                {
                    "access_token": str(refresh.access_token),
                },
                status=status.HTTP_200_OK,
            )
        except (TokenError, InvalidToken):
            return Response(
                {"error": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
