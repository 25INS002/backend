from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    PHYSICAL_ID_CHOICES = (
        ("aadhar", "Aadhar"),
        ("passport", "Passport"),
        ("driver_license", "Driver License"),
        ("college_id", "College ID"),
        ("other", "Other"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    dob = models.DateField()  # Date of birth instead of age
    profile_picture = models.ImageField(upload_to="profile_pictures/", null=True, blank=True)
    physical_id_type = models.CharField(max_length=20, choices=PHYSICAL_ID_CHOICES)
    physical_id_photo = models.ImageField(upload_to="physical_ids/")  # stored in /media/physical_ids/
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def physical_id_url(self):
        if self.physical_id_photo:
            return self.physical_id_photo.url
        return None

    @property
    def profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None

    def __str__(self):
        return f"{self.user.username} profile"
