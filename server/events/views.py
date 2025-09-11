from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Event
from .serializers import EventSerializer
from accounts.auth import CookieJWTAuthentication


# --- Create Event (admin only) ---
class EventCreateView(generics.CreateAPIView):
    serializer_class = EventSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # only logged-in admins

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_staff and not user.is_superuser:
            raise permissions.PermissionDenied("Only admins can create events")
        serializer.save(admin=user)


# --- List Events ---
class EventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Event.objects.all()


# --- Retrieve Event ---
class EventRetrieveView(generics.RetrieveAPIView):
    serializer_class = EventSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Event.objects.all()
    lookup_field = "pk"


# Update Event (partial allowed)
class EventUpdateView(generics.UpdateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        # Only the admin who created the event or superusers can update
        user = self.request.user
        if user.is_superuser:
            return Event.objects.all()
        return Event.objects.filter(admin=user)

    def update(self, request, *args, **kwargs):
        partial = True  # <--- allow partial updates
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


# --- Delete Event (admin who created it or superadmin) ---
class EventDeleteView(generics.DestroyAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Event.objects.all()
    lookup_field = "pk"

    def perform_destroy(self, instance):
        user = self.request.user
        if not (user.is_superuser or instance.admin == user):
            raise permissions.PermissionDenied("You cannot delete this event")
        instance.delete()


# --- Add participant to event ---
class AddParticipantView(generics.UpdateAPIView):
    serializer_class = EventSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Event.objects.all()
    lookup_field = "pk"

    def post(self, request, *args, **kwargs):
        event = self.get_object()
        user_id = request.data.get("user_id")
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        event.participants.add(user)
        event.save()
        return Response(EventSerializer(event).data, status=status.HTTP_200_OK)
