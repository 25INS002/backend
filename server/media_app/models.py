from django.db import models
from django.contrib.auth.models import User

class MediaFile(models.Model):
    MEDIA_TYPES = (
        ("image", "Image"),
        ("video", "Video"),
        ("file", "File"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploads")
    file = models.FileField(upload_to="uploads/")   # stored in /media/uploads/
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.file.name}"
