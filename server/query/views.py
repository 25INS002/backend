# views.py
from rest_framework import generics, permissions
from .models import ContactMessage
from .serializers import ContactMessageCreateSerializer
from .serializers import ContactMessageAdminSerializer
from accounts.auth import CookieJWTAuthentication
from adminpanel.permissions import IsAdminOrSuperAdmin
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q




class ContactMessageCreateView(generics.CreateAPIView):
    serializer_class = ContactMessageCreateSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        request = self.request
        instance = serializer.save(
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )
        
        # Notify Admin
        from utils.util import send_notification_email
        from django.conf import settings
        
        # Send to default system email or a specific admin email
        admin_email = getattr(settings, "DEFAULT_FROM_EMAIL", "admin@i2edc.org")
        
        send_notification_email(
            recipient_email=admin_email,
            template_type="contact_form",
            context={
                "name": instance.name,
                "email": instance.email,
                "subject": instance.subject,
                "message": instance.message,
            }
        )

class ContactMessageAdminUpdateView(generics.RetrieveUpdateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageAdminSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

class ContactMessageAdminListView(generics.ListAPIView):
    """
    Admin / SuperAdmin inbox for contact form submissions
    """

    serializer_class = ContactMessageAdminSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        queryset = ContactMessage.objects.all()

        # --- Filters ---
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status.upper())

        # --- Search ---
        search = self.request.query_params.get("q")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(subject__icontains=search)
                | Q(message__icontains=search)
            )

        return queryset.order_by("-created_at")

