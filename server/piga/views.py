from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
import json

from .models import PigaApplication
from .serializers import (
    PigaApplicationSerializer,
    PigaApplicationCreateSerializer,
    PigaApplicationUpdateSerializer,
    PigaAdminUpdateSerializer,
    PigaApplicationListSerializer,
)
from accounts.auth import CookieJWTAuthentication
from adminpanel.permissions import IsSuperAdmin, IsAdminOrSuperAdmin


# ===================================================================
# 1. USER ENDPOINTS — Submit & Track Applications
# ===================================================================


class PigaSubmitView(generics.CreateAPIView):
    """Submit a new PIGA application (any authenticated user)."""
    serializer_class = PigaApplicationCreateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()


class MyPigaListView(generics.ListAPIView):
    """List all PIGA applications submitted by the current user."""
    serializer_class = PigaApplicationSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            PigaApplication.objects.filter(applicant=self.request.user)
            .select_related("applicant", "reviewed_by")
            .order_by("-submitted_at")
        )


class MyPigaDetailView(generics.RetrieveAPIView):
    """Retrieve a specific PIGA application (owner only)."""
    serializer_class = PigaApplicationSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PigaApplication.objects.filter(applicant=self.request.user)


class MyPigaUpdateView(generics.UpdateAPIView):
    """
    Update a PIGA application (owner only).
    Only allowed when status is PENDING or REVIEW_BACK.
    After resubmitting (when REVIEW_BACK), status resets to PENDING.
    """
    serializer_class = PigaApplicationUpdateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return PigaApplication.objects.filter(
            applicant=self.request.user,
            status__in=["PENDING", "REVIEW_BACK"],
        )

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        instance = self.get_object()

        # If user is resubmitting after review-back, reset status to PENDING
        if instance.status == "REVIEW_BACK":
            instance.status = "PENDING"
            instance.review_feedback = ""
            instance.save(update_fields=["status", "review_feedback"])

        return super().update(request, *args, **kwargs)


class MyPigaStatisticsView(generics.GenericAPIView):
    """Get statistics for the current user's PIGA applications."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_apps = PigaApplication.objects.filter(applicant=request.user)

        return Response({
            "total": user_apps.count(),
            "pending": user_apps.filter(status="PENDING").count(),
            "under_review": user_apps.filter(status="UNDER_REVIEW").count(),
            "review_back": user_apps.filter(status="REVIEW_BACK").count(),
            "approved": user_apps.filter(status="APPROVED").count(),
            "rejected": user_apps.filter(status="REJECTED").count(),
        })


# ===================================================================
# 2. ADMIN ENDPOINTS — Review & Manage Applications
# ===================================================================


class AdminPigaListView(generics.ListAPIView):
    """
    List all PIGA applications (Admin/SuperAdmin).
    Supports ?status=PENDING query param for filtering.
    """
    serializer_class = PigaApplicationListSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        queryset = (
            PigaApplication.objects
            .select_related("applicant", "reviewed_by")
            .order_by("-submitted_at")
        )

        # Filter by status
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        # Search by project title or applicant name
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(project_title__icontains=search)
                | Q(full_name__icontains=search)
                | Q(email__icontains=search)
                | Q(organisation__icontains=search)
            )

        return queryset


class AdminPigaDetailView(generics.RetrieveAPIView):
    """Retrieve full detail of a PIGA application (Admin/SuperAdmin)."""
    serializer_class = PigaApplicationSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    queryset = PigaApplication.objects.all()


class AdminPigaUpdateView(generics.UpdateAPIView):
    """
    Update a PIGA application's status (Admin/SuperAdmin).
    Supports: APPROVED, REJECTED, UNDER_REVIEW, REVIEW_BACK.
    Must include review_feedback when sending back or rejecting.
    """
    serializer_class = PigaAdminUpdateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = "pk"
    queryset = PigaApplication.objects.all()

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class AdminPigaStatisticsView(generics.GenericAPIView):
    """Get overall PIGA statistics (Admin/SuperAdmin)."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def get(self, request):
        apps = PigaApplication.objects.all()

        return Response({
            "total": apps.count(),
            "pending": apps.filter(status="PENDING").count(),
            "under_review": apps.filter(status="UNDER_REVIEW").count(),
            "review_back": apps.filter(status="REVIEW_BACK").count(),
            "approved": apps.filter(status="APPROVED").count(),
            "rejected": apps.filter(status="REJECTED").count(),
        })


# ===================================================================
# 3. REMARKS — Chat-like messages (same pattern as services)
# ===================================================================


@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def append_piga_remark(request, pk):
    """
    Append a remark/message to a PIGA application.
    Works for BOTH admin and the applicant.
    """
    with transaction.atomic():
        application = get_object_or_404(PigaApplication, pk=pk)

        # Permission: only the applicant or admin/superadmin can add remarks
        user = request.user
        is_admin = (
            getattr(user, "is_superadmin", False)
            or user.is_superuser
            or user.is_staff
        )
        is_owner = (user == application.applicant)

        if not (is_admin or is_owner):
            return Response(
                {"error": "You do not have permission to add a remark."},
                status=status.HTTP_403_FORBIDDEN,
            )

        message = request.data.get("message", "").strip()
        if not message:
            return Response(
                {"error": "Message cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(message) > 2000:
            return Response(
                {"error": "Message too long (max 2000 characters)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        remark_entry = {
            "by": "admin" if is_admin else "user",
            "user_id": user.id,
            "username": user.username,
            "message": message,
            "timestamp": timezone.now().isoformat(),
        }

        if application.remark:
            application.remark += "\n" + json.dumps(remark_entry)
        else:
            application.remark = json.dumps(remark_entry)

        application.save(update_fields=["remark"])

        # --- Send Email Notifications ---
        from utils.util import send_notification_email

        def send_remark_email(target_user, is_sender):
            if not target_user or not target_user.email:
                return
            if is_sender:
                send_notification_email(
                    recipient_email=target_user.email,
                    template_type="piga_remark_sender",
                    context={
                        "project_title": application.project_title,
                        "message": message,
                    },
                )
            else:
                send_notification_email(
                    recipient_email=target_user.email,
                    template_type="piga_remark_recipient",
                    context={
                        "project_title": application.project_title,
                        "sender_name": user.username,
                        "message": message,
                    },
                )

        # Email the applicant
        send_remark_email(application.applicant, is_owner)

        # Email admins who have reviewed this application
        if application.reviewed_by and application.reviewed_by != application.applicant:
            send_remark_email(
                application.reviewed_by,
                user == application.reviewed_by,
            )

        return Response(
            {"message": "Remark added successfully.", "remark": remark_entry},
            status=status.HTTP_201_CREATED,
        )
