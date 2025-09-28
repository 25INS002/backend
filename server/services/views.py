from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
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
    queryset = Service.objects.all().prefetch_related('availability_slots').select_related('admin')
    serializer_class = ServiceListSerializer  # Use lightweight serializer for list view

    def get_serializer_class(self):
        # Use detailed serializer for authenticated users if needed
        if self.request.user.is_authenticated:
            return ServiceSerializer
        return ServiceListSerializer

# Retrieve a single service's details (Open to everyone)
class ServiceRetrieveView(generics.RetrieveAPIView):
    queryset = Service.objects.all().prefetch_related('availability_slots').select_related('admin')
    serializer_class = ServiceSerializer

# Update a service (Only the admin who created it or a SuperAdmin)
class ServiceUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'is_superadmin', False) or user.is_superuser:
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
        if getattr(user, 'is_superadmin', False) or user.is_superuser:
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
        service_pk = self.kwargs['service_pk']
        return Availability.objects.filter(service_id=service_pk)

    def perform_create(self, serializer):
        service = generics.get_object_or_404(Service, pk=self.kwargs['service_pk'])
        # Ensure only the service owner or superadmin can add availability
        if service.admin == self.request.user or getattr(self.request.user, 'is_superadmin', False) or self.request.user.is_superuser:
            serializer.save(service=service)
        else:
            raise PermissionDenied("You do not have permission to add availability to this service.")

# Retrieve, update, or delete a specific availability slot
class AvailabilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AvailabilitySerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = 'pk'

    def get_queryset(self):
        service_pk = self.kwargs['service_pk']
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
        return ServiceRequest.objects.filter(
            requested_by=self.request.user
        ).select_related('service', 'requested_by').order_by('-requested_at')

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
    lookup_field = 'pk'

    def get_queryset(self):
        return ServiceRequest.objects.filter(
            requested_by=self.request.user,
            status__in=['PENDING', 'APPROVED']  # Only allow updates for certain statuses
        )

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

# Cancel a service request (owner only)
class ServiceRequestCancelView(generics.UpdateAPIView):
    serializer_class = ServiceRequestSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return ServiceRequest.objects.filter(requested_by=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if not instance.can_be_cancelled():
            return Response(
                {"error": "This request cannot be cancelled in its current status."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.status = 'CANCELLED'
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
        status_filter = self.request.query_params.get('status', None)
        
        queryset = ServiceRequest.objects.select_related(
            'service', 'requested_by', 'service__admin'
        ).order_by('-requested_at')
        
        if getattr(user, 'is_superadmin', False) or user.is_superuser:
            # SuperAdmin sees all requests
            pass
        else:
            # Regular admin sees only requests for their services
            queryset = queryset.filter(service__admin=user)
        
        # Filter by status if provided
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        return queryset

# Update a service request's status or remark (Admin/SuperAdmin)
class AdminServiceRequestUpdateView(generics.UpdateAPIView):
    serializer_class = AdminServiceRequestUpdateSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    lookup_field = 'pk'

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'is_superadmin', False) or user.is_superuser:
            return ServiceRequest.objects.all()
        return ServiceRequest.objects.filter(service__admin=user)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

# ===================================================================
# 5. ADDITIONAL FEATURE VIEWS
# ===================================================================

# Check service availability
@api_view(['POST'])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def check_service_availability(request, service_pk):
    """
    Check if a service is available at a specific day and time
    """
    service = generics.get_object_or_404(Service, pk=service_pk)
    serializer = AvailabilityCheckSerializer(data=request.data)
    
    if serializer.is_valid():
        day_of_week = serializer.validated_data['day_of_week']
        time = serializer.validated_data['time']
        
        is_available = service.is_available_on(day_of_week, time)
        
        return Response({
            'service': service.name,
            'day_of_week': day_of_week,
            'time': time.strftime('%H:%M'),
            'is_available': is_available
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Get service statistics for admin
@api_view(['GET'])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([IsAdminOrSuperAdmin])
def service_statistics(request, service_pk):
    """
    Get statistics for a specific service
    """
    service = generics.get_object_or_404(Service, pk=service_pk)
    
    # Check permission
    user = request.user
    if not (getattr(user, 'is_superadmin', False) or user.is_superuser or service.admin == user):
        raise PermissionDenied("You don't have permission to view statistics for this service.")
    
    # Calculate statistics
    total_requests = ServiceRequest.objects.filter(service=service).count()
    pending_requests = ServiceRequest.objects.filter(service=service, status='PENDING').count()
    completed_requests = ServiceRequest.objects.filter(service=service, status='COMPLETED').count()
    
    # Get popular plans
    popular_plans = ServiceRequest.objects.filter(service=service).values(
        'plan__plan'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    statistics_data = {
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'completed_requests': completed_requests,
        'popular_plans': list(popular_plans)
    }
    
    serializer = ServiceStatisticsSerializer(statistics_data)
    return Response(serializer.data)

# Get user's service request statistics
@api_view(['GET'])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([permissions.IsAuthenticated])
def my_requests_statistics(request):
    """
    Get statistics for the current user's service requests
    """
    user_requests = ServiceRequest.objects.filter(requested_by=request.user)
    
    total_requests = user_requests.count()
    pending_requests = user_requests.filter(status='PENDING').count()
    approved_requests = user_requests.filter(status='APPROVED').count()
    in_progress_requests = user_requests.filter(status='IN_PROGRESS').count()
    completed_requests = user_requests.filter(status='COMPLETED').count()
    cancelled_requests = user_requests.filter(status='CANCELLED').count()
    
    return Response({
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'in_progress_requests': in_progress_requests,
        'completed_requests': completed_requests,
        'cancelled_requests': cancelled_requests,
    })

# Get services by current admin
class MyServicesListView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def get_queryset(self):
        return Service.objects.filter(admin=self.request.user).prefetch_related('availability_slots')

# Search services
class ServiceSearchView(generics.ListAPIView):
    serializer_class = ServiceListSerializer

    def get_queryset(self):
        queryset = Service.objects.all().select_related('admin')
        search_query = self.request.query_params.get('q', None)
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(long_description__icontains=search_query)
            )
        
        return queryset

# Get available plans for a service
@api_view(['GET'])
def service_plans(request, service_pk):
    """
    Get available plans for a specific service
    """
    service = generics.get_object_or_404(Service, pk=service_pk)
    plans = service.get_available_plans()
    
    return Response({
        'service': service.name,
        'plans': plans
    })

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
        if not (service.admin == request.user or getattr(request.user, 'is_superadmin', False) or request.user.is_superuser):
            raise PermissionDenied("You don't have permission to update availability for this service.")
        
        serializer = self.get_serializer(data=request.data, many=True)
        
        if serializer.is_valid():
            # Delete existing availability slots
            service.availability_slots.all().delete()
            
            # Create new availability slots
            availability_slots = []
            for slot_data in serializer.validated_data:
                availability_slots.append(Availability(service=service, **slot_data))
            
            Availability.objects.bulk_create(availability_slots)
            
            return Response({
                "message": f"Successfully updated {len(availability_slots)} availability slots",
                "slots": AvailabilitySerializer(service.availability_slots.all(), many=True).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)