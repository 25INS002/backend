# serializers.py
from rest_framework import serializers
from .models import ContactMessage

class ContactMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]

    def validate_message(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Message too short.")
        return value

class ContactMessageAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = "__all__"
        read_only_fields = ["name", "email", "subject", "message", "created_at", "ip_address", "user_agent"]
