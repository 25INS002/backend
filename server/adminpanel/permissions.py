from rest_framework import permissions

class IsSuperAdmin(permissions.BasePermission):
    """Only superadmins (is_superuser) can access."""
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_superuser)

class IsAdminOrSuperAdmin(permissions.BasePermission):
    """Admins (is_staff) or superadmins can access."""
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))
