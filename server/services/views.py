from rest_framework import generics, permissions
from .models import Service
from .serializers import ServiceSerializer
from accounts.auth import CookieJWTAuthentication
from adminpanel.permissions import IsSuperAdmin, IsAdminOrSuperAdmin
# Create service (only admins)
class ServiceCreateView(generics.CreateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin or IsSuperAdmin]

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)


# List all services
class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin or IsAdminOrSuperAdmin]


# Update service (partial update allowed, only admin who created it or superadmin)
class ServiceUpdateView(generics.UpdateAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin or IsSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Service.objects.all()
        return Service.objects.filter(admin=user)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


# Delete service (only admin who created it or superadmin)
class ServiceDeleteView(generics.DestroyAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin or IsSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Service.objects.all()
        return Service.objects.filter(admin=user)
