from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from django.shortcuts import get_object_or_404
import json
from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.utils import timezone
from .models import Service, Availability, ServiceRequest
from .serializers import (
    ServiceSerializer,
    ServiceListSerializer,
    AvailabilitySerializer,
    AvailabilityNestedSerializer,
    ServiceRequestSerializer,
    ServiceRequestCreateSerializer,
    ServiceRequestUpdateSerializer,
    AdminServiceRequestUpdateSerializer,
    AvailabilityCheckSerializer,
    ServiceStatisticsSerializer,
    UserSerializer,
)
from accounts.auth import CookieJWTAuthentication
from adminpanel.permissions import IsSuperAdmin, IsAdminOrSuperAdmin
import datetime

# ===================================================================
# 1. SERVICE API VIEWS (for Admins/SuperAdmins)
# ===================================================================


# Create a service (Admins and SuperAdmins)
class ServiceCreateView(generics.CreateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def perform_create(self, serializer):
        # The admin is automatically set in the serializer from context
        serializer.save()


# List all services (Open to everyone, including unauthenticated users)
class ServiceListView(generics.ListAPIView):
    queryset = (
        Service.objects.all()
        .prefetch_related("availability_slots")
        .select_related("admin")
    )
    serializer_class = ServiceListSerializer  # Use lightweight serializer for list view

    def get_serializer_class(self):
        # Use detailed serializer for authenticated users if needed
        if self.request.user.is_authenticated:
            return ServiceSerializer
        return ServiceListSerializer


# Retrieve a single service's details (Open to everyone)
class ServiceRetrieveView(generics.RetrieveAPIView):
    queryset = (
        Service.objects.all()
        .prefetch_related("availability_slots")
        .select_related("admin")
    )
    serializer_class = ServiceSerializer


# Update a service (Only the admin who created it or a SuperAdmin)
class ServiceUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_superadmin", False) or user.is_superuser:
            return Service.objects.all()
        return Service.objects.filter(admin=user)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True  # Allow partial updates (PATCH)
        return super().update(request, *args, **kwargs)


# Delete a service (Only the admin who created it or a SuperAdmin)
class ServiceDeleteView(generics.DestroyAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_superadmin", False) or user.is_superuser:
            return Service.objects.all()
        return Service.objects.filter(admin=user)


# ===================================================================
# 2. AVAILABILITY API VIEWS (for Admins/SuperAdmins)
# Nested under a specific service
# ===================================================================


# List and create availability slots for a specific service
class AvailabilityListCreateView(generics.ListCreateAPIView):
    serializer_class = AvailabilitySerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        service_pk = self.kwargs["service_pk"]
        return Availability.objects.filter(service_id=service_pk)

    def perform_create(self, serializer):
        service = generics.get_object_or_404(Service, pk=self.kwargs["service_pk"])
        # Ensure only the service owner or superadmin can add availability
        if (
            service.admin == self.request.user
            or getattr(self.request.user, "is_superadmin", False)
            or self.request.user.is_superuser
        ):
            serializer.save(service=service)
        else:
            raise PermissionDenied(
                "You do not have permission to add availability to this service."
            )


# Retrieve, update, or delete a specific availability slot
class AvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        service_pk = self.kwargs["service_pk"]
        return Availability.objects.filter(service_id=service_pk)


# ===================================================================
# 3. SERVICE REQUEST API VIEWS (for Regular Users)
# ===================================================================


# Create a service request (Any authenticated user)
class ServiceRequestCreateView(generics.CreateAPIView):
    serializer_class = ServiceRequestCreateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # requested_by is automatically set in the serializer from context
        serializer.save()


# List all service requests made by the current user
class MyServiceRequestListView(generics.ListAPIView):
    serializer_class = ServiceRequestSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            ServiceRequest.objects.filter(requested_by=self.request.user)
            .select_related("service", "requested_by")
            .order_by("-requested_at")
        )


# Retrieve a specific service request (owner only)
class MyServiceRequestDetailView(generics.RetrieveAPIView):
    serializer_class = ServiceRequestSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ServiceRequest.objects.filter(requested_by=self.request.user)


# Update a service request (owner only - only certain fields)
class MyServiceRequestUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceRequestUpdateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            requested_by=self.request.user,
            status__in=[
                "PENDING",
                "APPROVED",
                "IN_PROGRESS"
            ],  # Only allow updates for certain statuses
        )

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


# Cancel a service request (owner only)
class ServiceRequestCancelView(generics.UpdateAPIView):
    serializer_class = ServiceRequestSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return ServiceRequest.objects.filter(requested_by=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance.can_be_cancelled():
            return Response(
                {"error": "This request cannot be cancelled in its current status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.status = "CANCELLED"
        instance.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ===================================================================
# 4. SERVICE REQUEST MANAGEMENT API VIEWS (for Admins/SuperAdmins)
# ===================================================================


# List all service requests for services managed by the admin/superadmin
class AdminServiceRequestListView(generics.ListAPIView):
    serializer_class = ServiceRequestSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        status_filter = self.request.query_params.get("status", None)

        queryset = ServiceRequest.objects.select_related(
            "service", "requested_by", "service__admin"
        ).order_by("-requested_at")

        if getattr(user, "is_superadmin", False) or user.is_superuser:
            # SuperAdmin sees all requests
            pass
        else:
            # Regular admin sees only requests for their services
            queryset = queryset.filter(service__admin=user)

        # Filter by status if provided
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())

        return queryset


class AdminServiceRequestRetrieveView(generics.RetrieveAPIView):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer


# Update a service request's status or remark (Admin/SuperAdmin)
class AdminServiceRequestUpdateView(generics.UpdateAPIView):
    serializer_class = AdminServiceRequestUpdateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_superadmin", False) or user.is_superuser:
            return ServiceRequest.objects.all()
        return ServiceRequest.objects.filter(service__admin=user)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


# ===================================================================
# 5. ADDITIONAL FEATURE VIEWS
# ===================================================================
def can_add_remark(user, service_request):
    """
    User can add remark if:
    - they are the request owner
    - OR they are admin of the service
    - OR they are superadmin
    """
    if user == service_request.requested_by:
        return True

    if (
        getattr(user, "is_superadmin", False)
        or user.is_superuser
        or service_request.service.admin == user
    ):
        return True

    return False


@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def append_service_request_remark(request, pk):
    """
    Append a remark to a service request.
    Works for BOTH admin and user.
    """
    with transaction.atomic():
        service_request = get_object_or_404(ServiceRequest, pk=pk)

        # Permission check
        if not can_add_remark(request.user, service_request):
            return Response(
                {"error": "You do not have permission to add a remark to this request."},
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

        # Build structured remark entry
        remark_entry = {
            "by": "admin" if (
                getattr(request.user, "is_superadmin", False)
                or request.user.is_superuser
                or service_request.service.admin == request.user
            ) else "user",
            "user_id": request.user.id,
            "username": request.user.username,
            "message": message,
            "timestamp": timezone.now().isoformat(),
        }

        # Append safely
        if service_request.remark:
            service_request.remark += "\n" + json.dumps(remark_entry)
        else:
            service_request.remark = json.dumps(remark_entry)

        service_request.save(update_fields=["remark"])

        # --- Send Email Notifications (Chat) ---
        from utils.util import send_notification_email  # Local import
        
        # Helper to send correct template
        def send_remark_email(target_user, is_sender_of_msg):
            if not target_user or not target_user.email:
                return
                
            if is_sender_of_msg:
                # To Self (Confirmation)
                send_notification_email(
                    recipient_email=target_user.email,
                    template_type="service_remark_sender",
                    context={
                        "service_name": service_request.service.name,
                        "message": message,
                    }
                )
            else:
                # To Other (Notification)
                send_notification_email(
                    recipient_email=target_user.email,
                    template_type="service_remark_recipient",
                    context={
                        "service_name": service_request.service.name,
                        "sender_name": request.user.username, # The one who triggered this view
                        "message": message,
                    }
                )

        # 1. Handle Admin Email
        service_admin = service_request.service.admin
        # Check if Admin is the one sending the message
        is_admin_sender = (request.user == service_admin)
        send_remark_email(service_admin, is_admin_sender)

        # 2. Handle User Email
        requesting_user = service_request.requested_by
        # Check if User is the one sending the message
        is_user_sender = (request.user == requesting_user)
        send_remark_email(requesting_user, is_user_sender)

        return Response(
            {
                "message": "Remark added successfully.",
                "remark": remark_entry,
            },
            status=status.HTTP_201_CREATED,
        )


# Check service availability
@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def check_service_availability(request, service_pk):
    """
    Check if a service is available at a specific day and time
    """
    service = generics.get_object_or_404(Service, pk=service_pk)
    serializer = AvailabilityCheckSerializer(data=request.data)

    if serializer.is_valid():
        day_of_week = serializer.validated_data["day_of_week"]
        time = serializer.validated_data["time"]

        is_available = service.is_available_on(day_of_week, time)

        return Response(
            {
                "service": service.name,
                "day_of_week": day_of_week,
                "time": time.strftime("%H:%M"),
                "is_available": is_available,
            }
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Get service statistics for admin
@api_view(["GET"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAdminOrSuperAdmin])
def service_statistics(request, service_pk):
    """
    Get statistics for a specific service
    """
    service = generics.get_object_or_404(Service, pk=service_pk)

    # Check permission
    user = request.user
    if not (
        getattr(user, "is_superadmin", False)
        or user.is_superuser
        or service.admin == user
    ):
        raise PermissionDenied(
            "You don't have permission to view statistics for this service."
        )

    # Calculate statistics
    total_requests = ServiceRequest.objects.filter(service=service).count()
    pending_requests = ServiceRequest.objects.filter(
        service=service, status="PENDING"
    ).count()
    completed_requests = ServiceRequest.objects.filter(
        service=service, status="COMPLETED"
    ).count()

    # Get popular plans
    popular_plans = (
        ServiceRequest.objects.filter(service=service)
        .values("plan__plan")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )

    statistics_data = {
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "completed_requests": completed_requests,
        "popular_plans": list(popular_plans),
    }

    serializer = ServiceStatisticsSerializer(statistics_data)
    return Response(serializer.data)


# Get user's service request statistics
@api_view(["GET"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def my_requests_statistics(request):
    """
    Get statistics for the current user's service requests
    """
    user_requests = ServiceRequest.objects.filter(requested_by=request.user)

    total_requests = user_requests.count()
    pending_requests = user_requests.filter(status="PENDING").count()
    approved_requests = user_requests.filter(status="APPROVED").count()
    in_progress_requests = user_requests.filter(status="IN_PROGRESS").count()
    completed_requests = user_requests.filter(status="COMPLETED").count()
    cancelled_requests = user_requests.filter(status="CANCELLED").count()

    return Response(
        {
            "total_requests": total_requests,
            "pending_requests": pending_requests,
            "approved_requests": approved_requests,
            "in_progress_requests": in_progress_requests,
            "completed_requests": completed_requests,
            "cancelled_requests": cancelled_requests,
        }
    )


# --- Get services by current admin ---
class MyServicesListView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            # superadmins can see all services
            return Service.objects.all().prefetch_related("availability_slots")
        # normal admins see only their own services
        return Service.objects.filter(admin=user).prefetch_related("availability_slots")


# Search services
class ServiceSearchView(generics.ListAPIView):
    serializer_class = ServiceListSerializer

    def get_queryset(self):
        queryset = Service.objects.all().select_related("admin")
        search_query = self.request.query_params.get("q", None)

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(long_description__icontains=search_query)
            )

        return queryset


# Get available plans for a service
@api_view(["GET"])
def service_plans(request, service_pk):
    """
    Get available plans for a specific service
    """
    service = generics.get_object_or_404(Service, pk=service_pk)
    plans = service.get_available_plans()

    return Response({"service": service.name, "plans": plans})


# ===================================================================
# 6. BULK OPERATIONS
# ===================================================================


# Bulk update availability slots
class BulkAvailabilityUpdateView(generics.GenericAPIView):
    serializer_class = AvailabilityNestedSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request, service_pk):
        service = generics.get_object_or_404(Service, pk=service_pk)

        # Check permission
        if not (
            service.admin == request.user
            or getattr(request.user, "is_superadmin", False)
            or request.user.is_superuser
        ):
            raise PermissionDenied(
                "You don't have permission to update availability for this service."
            )

        serializer = self.get_serializer(data=request.data, many=True)

        if serializer.is_valid():
            # Delete existing availability slots
            service.availability_slots.all().delete()

            # Create new availability slots
            availability_slots = []
            for slot_data in serializer.validated_data:
                availability_slots.append(Availability(service=service, **slot_data))

            Availability.objects.bulk_create(availability_slots)

            return Response(
                {
                    "message": f"Successfully updated {len(availability_slots)} availability slots",
                    "slots": AvailabilitySerializer(
                        service.availability_slots.all(), many=True
                    ).data,
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===================================================================
# 7. RAZORPAY PAYMENT VIEWS
# ===================================================================

import hmac
import hashlib
from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_exempt
from .models import Payment
from .serializers import (
    CreateOrderSerializer,
    VerifyPaymentSerializer,
    PaymentSerializer,
)


def get_razorpay_client():
    """Lazy initialization of Razorpay client — only called when payment views are hit."""
    import razorpay  # Lazy import to avoid startup crash if pkg_resources is missing
    key_id = django_settings.RAZORPAY_KEY_ID
    key_secret = django_settings.RAZORPAY_KEY_SECRET
    if not key_id or not key_secret:
        raise Exception(
            "Razorpay keys not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your .env file."
        )
    return razorpay.Client(auth=(key_id, key_secret))


@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def create_order(request):
    """
    Create a Razorpay order and a ServiceRequest with AWAITING_PAYMENT status.
    The amount is always calculated server-side from the service plan data.
    """
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    service_id = serializer.validated_data["service_id"]
    plan_data = serializer.validated_data["plan"]
    request_msg = serializer.validated_data["request_msg"]

    service = get_object_or_404(Service, pk=service_id)

    # Validate plan exists in service
    plan_name = plan_data.get("plan")
    matched_plan = None
    for sp in service.cost_discount:
        if sp.get("plan") == plan_name:
            matched_plan = sp
            break

    if not matched_plan:
        return Response(
            {"error": f"Plan '{plan_name}' not found for this service."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Calculate amount SERVER-SIDE (never trust frontend amount)
    cost = matched_plan.get("cost", 0)
    discount = matched_plan.get("discount", 0)
    final_price = cost - discount
    amount_in_paise = int(final_price * 100)

    if amount_in_paise <= 0:
        return Response(
            {"error": "Invalid amount. Final price must be greater than 0."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            # Create Razorpay order
            client = get_razorpay_client()
            razorpay_order = client.order.create(
                {
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "notes": {
                        "service_id": str(service.id),
                        "service_name": service.name,
                        "plan": plan_name,
                        "user": request.user.username,
                    },
                }
            )

            # Create ServiceRequest with AWAITING_PAYMENT
            service_request = ServiceRequest.objects.create(
                requested_by=request.user,
                service=service,
                plan=matched_plan,
                request_msg=request_msg,
                status="AWAITING_PAYMENT",
            )

            # Create Payment record
            payment = Payment.objects.create(
                service_request=service_request,
                razorpay_order_id=razorpay_order["id"],
                amount=amount_in_paise,
                currency="INR",
                status="CREATED",
            )

            return Response(
                {
                    "order_id": razorpay_order["id"],
                    "amount": amount_in_paise,
                    "currency": "INR",
                    "key_id": django_settings.RAZORPAY_KEY_ID,
                    "service_request_id": service_request.id,
                    "service_name": service.name,
                    "plan_name": plan_name,
                },
                status=status.HTTP_201_CREATED,
            )

    except Exception as e:
        return Response(
            {"error": f"Failed to create order: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def verify_payment(request):
    """
    Verify Razorpay payment signature and finalize the ServiceRequest.
    Uses HMAC SHA256 to verify the signature is authentic.
    """
    serializer = VerifyPaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    razorpay_order_id = serializer.validated_data["razorpay_order_id"]
    razorpay_payment_id = serializer.validated_data["razorpay_payment_id"]
    razorpay_signature = serializer.validated_data["razorpay_signature"]

    try:
        payment = Payment.objects.select_related("service_request").get(
            razorpay_order_id=razorpay_order_id
        )
    except Payment.DoesNotExist:
        return Response(
            {"error": "Payment record not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Ensure the payment belongs to the requesting user
    if payment.service_request.requested_by != request.user:
        return Response(
            {"error": "Unauthorized."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Already paid
    if payment.status == "PAID":
        return Response(
            {"message": "Payment already verified.", "status": "success"},
            status=status.HTTP_200_OK,
        )

    try:
        # Verify signature using Razorpay SDK
        client = get_razorpay_client()
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

        # Signature valid — mark as paid
        with transaction.atomic():
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = "PAID"
            payment.save()

            payment.service_request.status = "PENDING"
            payment.service_request.save()

        return Response(
            {
                "message": "Payment verified successfully.",
                "status": "success",
                "service_request_id": payment.service_request.id,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as sig_error:  # razorpay.errors.SignatureVerificationError
        # Signature invalid — mark as failed
        with transaction.atomic():
            payment.status = "FAILED"
            payment.save()

            payment.service_request.status = "CANCELLED"
            payment.service_request.save()

        return Response(
            {"error": "Payment verification failed. Invalid signature.", "status": "failed"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
def razorpay_webhook(request):
    """
    Razorpay server-to-server webhook callback.
    No JWT auth — verified using webhook signature instead.
    Acts as a safety net for missed browser-side verifications.
    """
    webhook_secret = django_settings.RAZORPAY_WEBHOOK_SECRET
    received_signature = request.headers.get("X-Razorpay-Signature", "")

    if not webhook_secret:
        return Response(
            {"error": "Webhook secret not configured."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Verify webhook signature
    try:
        client = get_razorpay_client()
        client.utility.verify_webhook_signature(
            request.body.decode("utf-8"),
            received_signature,
            webhook_secret,
        )
    except Exception as sig_error:  # razorpay.errors.SignatureVerificationError
        return Response(
            {"error": "Invalid webhook signature."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse the event
    payload = request.data
    event = payload.get("event", "")

    if event == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")
        payment_id = payment_entity.get("id")

        if order_id:
            try:
                with transaction.atomic():
                    payment = Payment.objects.select_related("service_request").get(
                        razorpay_order_id=order_id
                    )
                    if payment.status != "PAID":
                        payment.razorpay_payment_id = payment_id
                        payment.status = "PAID"
                        payment.save()

                        payment.service_request.status = "PENDING"
                        payment.service_request.save()
            except Payment.DoesNotExist:
                pass

    elif event == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")

        if order_id:
            try:
                with transaction.atomic():
                    payment = Payment.objects.select_related("service_request").get(
                        razorpay_order_id=order_id
                    )
                    if payment.status not in ["PAID", "FAILED"]:
                        payment.status = "FAILED"
                        payment.save()

                        payment.service_request.status = "CANCELLED"
                        payment.service_request.save()
            except Payment.DoesNotExist:
                pass

    return Response({"status": "ok"}, status=status.HTTP_200_OK)
