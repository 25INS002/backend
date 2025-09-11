from rest_framework import generics, permissions
from .models import MediaFile
from .serializers import MediaFileSerializer
from .auth import CookieJWTAuthentication

# Upload media
class MediaUploadView(generics.CreateAPIView):
    serializer_class = MediaFileSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# List current user's media
class MediaListView(generics.ListAPIView):
    serializer_class = MediaFileSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MediaFile.objects.filter(user=self.request.user)


# Delete media
class MediaDeleteView(generics.DestroyAPIView):
    serializer_class = MediaFileSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MediaFile.objects.filter(user=self.request.user)
