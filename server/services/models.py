from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import datetime

# This is the main model for the services you offer.
class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    long_description = models.TextField(blank=True, null=True)
    media = models.FileField(upload_to="services/media/", blank=True, null=True)

    # Example: [{"plan": "basic", "cost": 100, "discount": 10, "description": "Basic plan details"}, {"plan": "premium", "cost": 200, "description": "Premium plan details"}]
    cost_discount = models.JSONField(default=list, blank=True)

    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name="services")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# This model normalizes the availability of a service.
class Availability(models.Model):
    DAY_CHOICES = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
        ("SAT", "Saturday"),
        ("SUN", "Sunday"),
    ]
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="availability_slots")
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        # Ensures that each time slot for a service on a given day is unique.
        unique_together = ('service', 'day_of_week', 'start_time', 'end_time')
        verbose_name_plural = "Availabilities"

    def __str__(self):
        return f"{self.service.name} - {self.get_day_of_week_display()}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

# This new model will store all user requests for a service.
class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('IN_QUEUE', 'In Queue'),
        ('REJECTED', 'Rejected'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Foreign key to the user who made the request.
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_requests")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="requests")

    # Stores the selected plan from the Service's cost_discount.
    # Example: {"plan": "basic", "cost": 100, "discount": 10, "description": "Basic plan details"}
    plan = models.JSONField()

    # The current status of the request.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # A JSON field to store the request message with a subject and body.
    # Example: {"subject": "Inquiry about premium plan", "body": "I would like to know more..."}
    request_msg = models.JSONField()

    # A field to upload any media related to the request.
    media_url = models.FileField(upload_to='service_requests/media/', blank=True, null=True)

    # A text field for any internal remarks or notes.
    remark = models.TextField(blank=True, null=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Request for {self.service.name} by {self.requested_by.username} - Status: {self.status}"
