from django.db import models
from django.contrib.auth.models import User

class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    long_description = models.TextField(blank=True, null=True)
    media = models.FileField(upload_to="services/media/", blank=True, null=True)

    # Availability map (JSON field for flexibility)
    # Example: {"Mon-Fri": "9am-6pm", "Sat": "10am-2pm"}
    availability_map = models.JSONField(default=dict, blank=True)

    # Cost/Discount array (JSON field for flexibility)
    # Example: [{"plan": "basic", "cost": 100, "discount": 10}, {"plan": "premium", "cost": 200}]
    cost_discount = models.JSONField(default=list, blank=True)

    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="services")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
