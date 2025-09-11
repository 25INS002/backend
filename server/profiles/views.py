from rest_framework import generics, permissions
from .models import UserProfile
from .serializers import UserProfileSerializer
from .auth import CookieJWTAuthentication
from rest_framework import serializers

# Create profile (only if it doesn't exist)
class UserProfileCreateView(generics.CreateAPIView):
    serializer_class = UserProfileSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Prevent multiple profiles
        if hasattr(self.request.user, "profile"):
            raise serializers.ValidationError("Profile already exists.")
        serializer.save(user=self.request.user)

# Retrieve current user's profile
class UserProfileRetrieveView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

# Update (partial) current user's profile
class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    # Allow partial updates
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
