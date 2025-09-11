from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Module, AdminModuleAccess
from .serializers import ModuleSerializer, AdminModuleAccessSerializer
from accounts.auth import CookieJWTAuthentication
from adminpanel.permissions import IsSuperAdmin  # custom permission: only superadmins can manage modules

# --- CRUD Modules (Superadmin only) ---
class ModuleCreateView(generics.CreateAPIView):
    serializer_class = ModuleSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]

class ModuleListView(generics.ListAPIView):
    serializer_class = ModuleSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        return Module.objects.all()


class ModuleUpdateView(generics.UpdateAPIView):
    serializer_class = ModuleSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]
    queryset = Module.objects.all()
    lookup_field = "pk"


class ModuleDeleteView(generics.DestroyAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]
    queryset = Module.objects.all()
    lookup_field = "pk"


# --- Assign Module Access to Admin ---
class AssignModuleAccessView(generics.CreateAPIView):
    serializer_class = AdminModuleAccessSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        admin_id = request.data.get("admin")
        module_id = request.data.get("module")
        can_create = request.data.get("can_create", False)
        can_read = request.data.get("can_read", True)
        can_update = request.data.get("can_update", False)
        can_delete = request.data.get("can_delete", False)

        try:
            admin = User.objects.get(pk=admin_id, is_staff=True, is_superuser=False)
            module = Module.objects.get(pk=module_id)
        except User.DoesNotExist:
            return Response({"error": "Admin not found"}, status=status.HTTP_404_NOT_FOUND)
        except Module.DoesNotExist:
            return Response({"error": "Module not found"}, status=status.HTTP_404_NOT_FOUND)

        access, created = AdminModuleAccess.objects.get_or_create(
            admin=admin,
            module=module,
            defaults={
                "can_create": can_create,
                "can_read": can_read,
                "can_update": can_update,
                "can_delete": can_delete
            }
        )

        if not created:
            # Update existing permissions
            access.can_create = can_create
            access.can_read = can_read
            access.can_update = can_update
            access.can_delete = can_delete
            access.save()

        return Response(AdminModuleAccessSerializer(access).data, status=201)


# --- List Admin Modules ---
class ListAdminModulesView(generics.ListAPIView):
    serializer_class = AdminModuleAccessSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        admin_id = self.request.query_params.get("admin")
        if admin_id:
            return AdminModuleAccess.objects.filter(admin__id=admin_id)
        return AdminModuleAccess.objects.all()
