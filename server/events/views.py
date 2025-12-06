from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Event
from .serializers import EventSerializer
from .serializers import UserSerializer
from accounts.auth import CookieJWTAuthentication
from django.utils import timezone
from rest_framework.views import APIView


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

    def get_queryset(self):
        return Event.objects.all()


# --- List Events ---
class AdminEventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            # superusers can see everything
            return Event.objects.all()
        # regular admins only see their own events
        return Event.objects.filter(admin=user)


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
        partial = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Only superusers can change admin
        if "admin" in serializer.validated_data and not request.user.is_superuser:
            serializer.validated_data.pop("admin")

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
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        """
        POST /events/add-participant/<pk>/
        Adds the current user as participant to the event
        """
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user = request.user
        event.participants.add(user)
        event.save()

        return Response(
            {"message": "Registered successfully"}, status=status.HTTP_200_OK
        )


# --- Get Active Events (currently running) ---
class ActiveEventsView(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        now = timezone.now()
        return Event.objects.filter(date__lte=now, duration__gte=now)


# --- Get Finished Events ---
class FinishedEventsView(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        now = timezone.now()
        return Event.objects.filter(duration__lt=now)


# --- Get Scheduled Events (upcoming, not started yet) ---
class ScheduledEventsView(generics.ListAPIView):
    serializer_class = EventSerializer

    def get_queryset(self):
        now = timezone.now()
        return Event.objects.filter(date__gt=now)


# --- Get Events User Participated In ---
class UserEventsView(generics.ListAPIView):
    serializer_class = EventSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return user.events_participated.all()


# --- Check if current user participates in event ---
class CheckParticipationView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        """
        GET /events/<pk>/participants/me/
        """
        user = request.user
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND
            )

        is_participating = event.participants.filter(id=user.id).exists()
        return Response({"is_participating": is_participating})


class EventParticipantsView(generics.ListAPIView):
    """
    GET /events/<pk>/participants/
    Returns a list of all participants of a given event
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response(
                {"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND
            )

        participants = event.participants.all()
        serializer = UserSerializer(participants, many=True)
        return Response(serializer.data)
