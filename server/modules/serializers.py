from rest_framework import serializers
from .models import Module, AdminModuleAccess
from django.contrib.auth.models import User

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "name", "description"]

class AdminModuleAccessSerializer(serializers.ModelSerializer):
    admin_username = serializers.ReadOnlyField(source="admin.username")
    module_name = serializers.ReadOnlyField(source="module.name")

    class Meta:
        model = AdminModuleAccess
        fields = ["id", "admin", "admin_username", "module", "module_name", "can_create", "can_read", "can_update", "can_delete"]
