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
from .auth import CookieJWTAuthentication
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
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        

        if not username or not email or not password or not first_name or not last_name:
            return Response({"error": "All fields required"}, status=status.HTTP_400_BAD_REQUEST)

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
        user = User.objects.create_user(username=username, email=email, password=password, is_active=False, first_name=first_name, last_name=last_name)

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        otp_store[username] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production: send OTP via email/SMS
        return Response(
            {"message": "User created. Verify OTP to activate.", "otp": otp},
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
        otp = str(random.randint(100000, 999999))
        otp_store[username] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production → send OTP via email/SMS
        return Response(
            {"message": "OTP resent", "otp": otp}, status=status.HTTP_200_OK
        )


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
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"error": "Email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )

        user = authenticate(username=user.username, password=password)
        if user is None or not user.is_active:
            return Response(
                {"error": "Invalid credentials or inactive account"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        user.last_login = datetime.datetime.now()
        user.save()
        response = Response({"message": "Login successful"})
        # Set HttpOnly cookies
        response.set_cookie(
            "access_token", access_token, httponly=True, secure=False, samesite="Lax"
        )
        response.set_cookie(
            "refresh_token", str(refresh), httponly=True, secure=False, samesite="Lax"
        )
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

        otp = str(random.randint(100000, 999999))
        reset_otp_store[email] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production → send OTP via email/SMS, not in response
        return Response(
            {"message": "OTP sent to email", "otp": otp}, status=status.HTTP_200_OK
        )


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
        otp = str(random.randint(100000, 999999))
        reset_otp_store[email] = {
            "otp": otp,
            "expires_at": datetime.datetime.now() + datetime.timedelta(minutes=15),
        }

        # ⚠️ In production → send OTP via email/SMS
        return Response(
            {"message": "Reset OTP resent", "otp": otp}, status=status.HTTP_200_OK
        )


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
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
# --- GET LOGGED IN USER INFO ---
class UserDetailView(APIView):
    authentication_classes = [CookieJWTAuthentication]  # your custom cookie-based JWT auth
    permission_classes = [IsAuthenticated]

    def get(self, request):  # ✅ use GET (not POST)
        user = request.user  # already populated from the cookie

        if not user or not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
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
        })

# --- REFRESH TOKEN ---
class TokenRefreshView(APIView):
    """
    This view is specifically designed to work with HttpOnly cookies.
    It reads the refresh token from the request's cookies and, if valid,
    returns a new access token as an HttpOnly cookie.
    """
    permission_classes = [AllowAny] # No auth token is needed to refresh

    def post(self, request):
        # 1. Get the refresh token from the HttpOnly cookie
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response(
                {"error": "Refresh token not found in cookies."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 2. Validate the refresh token and generate a new access token
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)

            # 3. (Highly Recommended) Implement Refresh Token Rotation
            # This invalidates the old refresh token and issues a new one.
            new_refresh_token = str(refresh)

            # 4. Create a response object and set the new cookies
            response = Response({
                "detail": "Access token refreshed successfully."
            }, status=status.HTTP_200_OK)

            # NOTE: For production, set secure=True to ensure cookies are only sent over HTTPS.
            # SameSite='Lax' is a good default for security.
            response.set_cookie(
                key='access_token',
                value=new_access_token,
                httponly=True,
                secure=False,  # Change to True in production
                samesite='Lax'
            )
            
            response.set_cookie(
                key='refresh_token',
                value=new_refresh_token,
                httponly=True,
                secure=False,  # Change to True in production
                samesite='Lax'
            )

            return response

        except (TokenError, InvalidToken) as e:
            # This will catch expired or malformed tokens
            return Response(
                {"error": "Invalid or expired refresh token."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )