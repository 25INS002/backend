from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from .serializers import AdminUserSerializer
from .permissions import IsSuperAdmin, IsAdminOrSuperAdmin
from accounts.auth import CookieJWTAuthentication
from django.db.models import Q

# --- Create Admin (Superadmin only) ---
class CreateAdminView(generics.GenericAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return Response({"error": "All fields are required"}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username exists"}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email exists"}, status=400)

        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True,
            is_staff=True  # admin
        )
        return Response({"message": "Admin created"}, status=201)
# -- Get Users By Ids ---
class GetUsersByIdsView(generics.GenericAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]

    def post(self, request):
        user_ids = request.data.get("user_ids", [])
        if not isinstance(user_ids, list) or not all(isinstance(i, int) for i in user_ids):
            return Response({"error": "user_ids must be a list of integers"}, status=400)

        users = User.objects.filter(id__in=user_ids)
        serializer = AdminUserSerializer(users, many=True)
        return Response(serializer.data, status=200)

# --- List Users ---
class ListUsersView(generics.ListAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        if self.request.user.is_staff and not self.request.user.is_superuser:
            return User.objects.filter(is_staff=False, is_superuser=False)
        return User.objects.all()

# --- Get Only Admins (not superuser) ---
class GetAdminsView(generics.ListAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        return User.objects.filter(is_staff=True, is_superuser=False)
   
# --- Get Only Superadmins ---
class GetSuperAdminsView(generics.ListAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        return User.objects.filter(is_superuser=True)

# --- Get Both Admins and Superadmins ---
class GetAdminsAndSuperAdminsView(generics.ListAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAdminOrSuperAdmin]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        return User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))  # includes both staff (admins) and superusers

# --- Update User ---
class UpdateUserView(generics.UpdateAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = AdminUserSerializer
    lookup_field = "pk"

    def get_queryset(self):
        if self.request.user.is_staff and not self.request.user.is_superuser:
            return User.objects.filter(is_staff=False, is_superuser=False)
        return User.objects.all()


# --- Delete User ---
class DeleteUserView(generics.DestroyAPIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsSuperAdmin]
    lookup_field = "pk"

    def get_queryset(self):
        if self.request.user.is_staff and not self.request.user.is_superuser:
            return User.objects.filter(is_staff=False, is_superuser=False)
        return User.objects.all()
