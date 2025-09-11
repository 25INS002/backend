from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    physical_id_url = serializers.ReadOnlyField()
    profile_picture_url = serializers.ReadOnlyField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "gender",
            "dob",  # date of birth instead of age
            "profile_picture",
            "profile_picture_url",
            "physical_id_type",
            "physical_id_photo",
            "physical_id_url",
        ]
        read_only_fields = ["id", "physical_id_url", "profile_picture_url"]
