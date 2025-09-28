from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Service, Availability, ServiceRequest
from .serializers import (
    ServiceSerializer,
    AvailabilitySerializer,
    ServiceRequestSerializer,
    AdminServiceRequestUpdateSerializer,
)
from accounts.auth import CookieJWTAuthentication  
from adminpanel.permissions import IsSuperAdmin, IsAdminOrSuperAdmin 

# ===================================================================
# 1. SERVICE API VIEWS (for Admins/SuperAdmins)
# ===================================================================

# Create a service (Admins and SuperAdmins)
class ServiceCreateView(generics.CreateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)

# List all services (Open to everyone, including unauthenticated users)
class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.all().prefetch_related('availability_slots')
    serializer_class = ServiceSerializer

# Retrieve a single service's details (Open to everyone)
class ServiceRetrieveView(generics.RetrieveAPIView):
    queryset = Service.objects.all().prefetch_related('availability_slots')
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
        if service.admin == self.request.user or self.request.user.is_superuser:
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
    serializer_class = ServiceRequestSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

# List all service requests made by the current user
class MyServiceRequestListView(generics.ListAPIView):
    serializer_class = ServiceRequestSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ServiceRequest.objects.filter(requested_by=self.request.user)

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
        if getattr(user, 'is_superadmin', False) or user.is_superuser:
            return ServiceRequest.objects.all()
        # Return requests only for services managed by the current admin
        return ServiceRequest.objects.filter(service__admin=user)

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