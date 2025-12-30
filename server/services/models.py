from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime

def append_remark(instance, sender: str, message: str):
    timestamp = timezone.now().isoformat()
    line = f"[{sender}|{timestamp}]: {message.strip()}\n"

    instance.remark = (instance.remark or "") + line
    instance.save(update_fields=["remark"])

# This is the main model for the services you offer.
class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    long_description = models.TextField(blank=True, null=True)
    media = models.FileField(upload_to="services/media/", blank=True, null=True)

    # Example: [{"plan": "basic", "cost": 100, "discount": 10, "description": "Basic plan details"}, {"plan": "premium", "cost": 200, "description": "Premium plan details"}]
    cost_discount = models.JSONField(default=list, blank=True)

    admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="services"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_available_plans(self):
        """Return available plans with calculated prices"""
        plans = []
        for plan_data in self.cost_discount:
            cost = plan_data.get("cost", 0)
            discount = plan_data.get("discount", 0)
            final_price = cost - discount

            plans.append(
                {
                    "plan": plan_data.get("plan"),
                    "original_cost": cost,
                    "discount": discount,
                    "final_price": final_price,
                    "description": plan_data.get("description", ""),
                }
            )
        return plans

    def is_available_on(self, day_of_week, time):
        """Check if service is available at given day/time"""
        return self.availability_slots.filter(
            day_of_week=day_of_week, start_time__lte=time, end_time__gte=time
        ).exists()

    def get_plan_names(self):
        return ", ".join([plan.get("plan", "") for plan in self.cost_discount])

    get_plan_names.short_description = "Available Plans"

    class Meta:
        ordering = ["name"]


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
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="availability_slots"
    )
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        # Ensures that each time slot for a service on a given day is unique.
        unique_together = ("service", "day_of_week", "start_time", "end_time")
        verbose_name_plural = "Availabilities"
        indexes = [
            models.Index(fields=["service", "day_of_week"]),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.get_day_of_week_display()}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")

        # Check for overlapping time slots for the same service and day
        overlapping_slots = (
            Availability.objects.filter(
                service=self.service, day_of_week=self.day_of_week
            )
            .exclude(pk=self.pk)
            .filter(
                models.Q(start_time__lt=self.end_time, end_time__gt=self.start_time)
            )
        )

        if overlapping_slots.exists():
            raise ValidationError(
                "This time slot overlaps with an existing availability slot for the same day."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# This new model will store all user requests for a service.
class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("IN_QUEUE", "In Queue"),
        ("REJECTED", "Rejected"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    # Foreign key to the user who made the request.
    requested_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="service_requests"
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="requests"
    )

    # Stores the selected plan from the Service's cost_discount.
    # Example: {"plan": "basic", "cost": 100, "discount": 10, "description": "Basic plan details"}
    plan = models.JSONField()

    # The current status of the request.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    # A JSON field to store the request message with a subject and body.
    # Example: {"subject": "Inquiry about premium plan", "body": "I would like to know more..."}
    request_msg = models.JSONField()

    # A field to upload any media related to the request.
    media_url = models.FileField(
        upload_to="service_requests/media/", blank=True, null=True
    )

    # A text field for any internal remarks or notes.
    remark = models.TextField(blank=True, null=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "requested_at"]),
            models.Index(fields=["requested_by", "status"]),
            models.Index(fields=["service", "status"]),
        ]
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Request for {self.service.name} by {self.requested_by.username} - Status: {self.status}"

    def get_final_price(self):
        """Calculate final price after discount"""
        cost = self.plan.get("cost", 0)
        discount = self.plan.get("discount", 0)
        return cost - discount

    def can_be_cancelled(self):
        """Check if request can be cancelled"""
        non_cancellable_statuses = ["COMPLETED", "IN_PROGRESS", "CANCELLED"]
        return self.status not in non_cancellable_statuses

    def get_plan_name(self):
        return self.plan.get("plan", "N/A")

    get_plan_name.short_description = "Plan"

    def clean(self):
        # Validate that the selected plan exists in the service's cost_discount
        if self.service and self.plan:
            service_plans = [plan.get("plan") for plan in self.service.cost_discount]
            if self.plan.get("plan") not in service_plans:
                raise ValidationError("Selected plan is not available for this service")

        # Validate plan structure
        required_plan_fields = ["plan", "cost"]
        for field in required_plan_fields:
            if field not in self.plan:
                raise ValidationError(f"Plan must contain '{field}' field")

        # Validate request_msg structure
        if "subject" not in self.request_msg or "body" not in self.request_msg:
            raise ValidationError(
                "Request message must contain 'subject' and 'body' fields"
            )

        # Validate cost is a positive number
        cost = self.plan.get("cost", 0)
        if not isinstance(cost, (int, float)) or cost < 0:
            raise ValidationError("Cost must be a positive number")

        # Validate discount is not negative and not greater than cost
        discount = self.plan.get("discount", 0)
        if not isinstance(discount, (int, float)) or discount < 0:
            raise ValidationError("Discount must be a non-negative number")
        if discount > cost:
            raise ValidationError("Discount cannot be greater than cost")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# Signal handlers
@receiver(post_save, sender=ServiceRequest)
def handle_service_request_status(sender, instance, created, **kwargs):
    """
    Automatically handle status changes and send notifications
    """
    if created:
        # Send notification to service admin about new request
        # You can integrate with Django's messaging framework or send emails here
        print(f"New service request created: {instance}")
        # Example: send_mail_to_admin(instance)

    # Add any other automated workflows here
    # For example, if status changed to approved, send confirmation to user
    if not created:
        print(f"Service request updated: {instance} - New status: {instance.status}")
        # Example: notify_user_about_status_change(instance)


# Optional: Additional helper functions
def get_pending_requests_count(service=None):
    """Get count of pending requests, optionally filtered by service"""
    queryset = ServiceRequest.objects.filter(status="PENDING")
    if service:
        queryset = queryset.filter(service=service)
    return queryset.count()


def get_user_active_requests(user):
    """Get all active (non-completed, non-cancelled) requests for a user"""
    return ServiceRequest.objects.filter(requested_by=user).exclude(
        status__in=["COMPLETED", "CANCELLED", "REJECTED"]
    )


def get_service_popular_plans(service):
    """Get the most popular plans for a service based on request count"""
    from django.db.models import Count

    plans_data = (
        ServiceRequest.objects.filter(service=service)
        .values("plan")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return list(plans_data)
