from rest_framework import generics, permissions
from .models import Feedback
from .serializers import FeedbackSerializer
from accounts.auth import CookieJWTAuthentication

# Create feedback
class FeedbackCreateView(generics.CreateAPIView):
    serializer_class = FeedbackSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# List feedback for a module
class ModuleFeedbackListView(generics.ListAPIView):
    serializer_class = FeedbackSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        module_id = self.kwargs["module_id"]
        return Feedback.objects.filter(module_id=module_id)


# Update feedback (partial update allowed)
class FeedbackUpdateView(generics.UpdateAPIView):
    serializer_class = FeedbackSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Feedback.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


# Delete feedback
class FeedbackDeleteView(generics.DestroyAPIView):
    serializer_class = FeedbackSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Feedback.objects.filter(user=self.request.user)
