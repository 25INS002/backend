from rest_framework import serializers
from .models import MediaFile




class MediaFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFile
        fields = ["id", "file", "media_type", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]
