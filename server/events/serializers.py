from rest_framework import serializers
from .models import Event
from django.contrib.auth.models import User


class EventSerializer(serializers.ModelSerializer):
    media_url = serializers.ReadOnlyField()
    participants_usernames = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "date",
            "duration",
            "description",
            "long_description",
            "media",
            "media_url",
            "participants",
            "participants_usernames",
            "admin",
            "reg_end_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "participants_usernames", "created_at", "updated_at"]

    def get_participants_usernames(self, obj):
        return [user.username for user in obj.participants.all()]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]
