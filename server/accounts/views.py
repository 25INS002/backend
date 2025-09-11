from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
import random, datetime
from django.contrib.auth.hashers import make_password

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

        if not username or not email or not password:
            return Response({"error": "All fields required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered"}, status=status.HTTP_400_BAD_REQUEST)

        # Create inactive user (will be activated after OTP verification)
        user = User.objects.create_user(username=username, email=email, password=password, is_active=False)

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        otp_store[username] = {"otp": otp, "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15)}

        # ⚠️ In production: send OTP via email/SMS
        return Response({"message": "User created. Verify OTP to activate.", "otp": otp}, status=status.HTTP_201_CREATED)


# --- VERIFY OTP FOR SIGNUP ---
class VerifyOTPView(APIView):
    def post(self, request):
        username = request.data.get("username")
        otp = request.data.get("otp")

        if not username or not otp:
            return Response({"error": "Username and OTP required"}, status=status.HTTP_400_BAD_REQUEST)

        if username not in otp_store:
            return Response({"error": "No OTP found. Request again."}, status=status.HTTP_400_BAD_REQUEST)

        record = otp_store[username]
        if datetime.datetime.now() > record["expires_at"]:
            del otp_store[username]
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

        if record["otp"] != otp:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
            user.is_active = True
            user.save()
            del otp_store[username]
            return Response({"message": "Account verified. You can now log in."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)


# --- LOGIN (Email + Password, sets cookies) ---
class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        user = authenticate(username=user.username, password=password)
        if user is None or not user.is_active:
            return Response({"error": "Invalid credentials or inactive account"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response({"message": "Login successful"})
        # Set HttpOnly cookies
        response.set_cookie("access_token", access_token, httponly=True, secure=False, samesite="Lax")
        response.set_cookie("refresh_token", str(refresh), httponly=True, secure=False, samesite="Lax")
        return response


# --- LOGOUT (Clears cookies) ---
class LogoutView(APIView):
    def post(self, request):
        response = Response({"message": "Logged out"})
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response

# --- REQUEST RESET OTP ---
class RequestPasswordResetOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email not found"}, status=status.HTTP_404_NOT_FOUND)

        otp = str(random.randint(100000, 999999))
        reset_otp_store[email] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15)
        }

        # ⚠️ In production → send OTP via email/SMS, not in response
        return Response({"message": "OTP sent to email", "otp": otp}, status=status.HTTP_200_OK)


# --- VERIFY OTP & RESET PASSWORD ---
class ResetPasswordView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not email or not otp or not new_password:
            return Response({"error": "Email, OTP and new password required"}, status=status.HTTP_400_BAD_REQUEST)

        if email not in reset_otp_store:
            return Response({"error": "No OTP found. Request again."}, status=status.HTTP_400_BAD_REQUEST)

        record = reset_otp_store[email]
        if datetime.datetime.now() > record["expires_at"]:
            del reset_otp_store[email]
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

        if record["otp"] != otp:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()
            del reset_otp_store[email]
            return Response({"message": "Password reset successful"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)