from rest_framework import serializers
from .models import MediaFile
import os


class MediaFileSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='uploaded_at', read_only=True)
    
    class Meta:
        model = MediaFile
        fields = ["id", "file", "media_type", "uploaded_at", "created_at", "file_name", "file_size"]
        read_only_fields = ["id", "uploaded_at", "created_at", "file_name", "file_size"]
    
    def get_file_name(self, obj):
        if obj.file:
            return os.path.basename(obj.file.name)
        return None
    
    def get_file_size(self, obj):
        try:
            if obj.file:
                return obj.file.size
        except Exception:
            pass
        return None

