from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = None

        # 1️⃣ First priority: Authorization header (Bearer <token>)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ", 1)[1]

        # 2️⃣ Fallback: HttpOnly cookie
        if not raw_token:
            raw_token = request.COOKIES.get("access_token")

        # 🚫 No token anywhere
        if not raw_token:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except Exception:
            raise AuthenticationFailed("Invalid or expired token")
