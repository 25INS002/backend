from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class PigaApplication(models.Model):
    """
    PIGA (Pitch Idea Grant Application) submission.
    Stores the 2-step form data: applicant details + pitch template.
    Admins/Heads can approve, reject, or send back for review.
    Users can track their application status.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("UNDER_REVIEW", "Under Review"),
        ("REVIEW_BACK", "Sent Back for Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    # ——— Applicant (linked to auth user) ———
    applicant = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="piga_applications"
    )

    # ——— Step 1: Applicant Details ———
    project_title = models.CharField(max_length=300)
    date = models.DateField()
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    organisation = models.CharField(max_length=300)

    # ——— Step 2: Pitch Template (10 sections) ———
    elevator_pitch = models.TextField(help_text="Brief elevator pitch of the idea")
    team = models.TextField(help_text="Team members and their roles")
    problem_opportunity = models.TextField(help_text="Problem or opportunity being addressed")
    solution_technology = models.TextField(help_text="Proposed solution or technology")
    current_status = models.TextField(help_text="Current status or stage of the project")
    unique_value_proposition = models.TextField(help_text="What makes this unique")
    cost_budget = models.TextField(help_text="Cost and budget bifurcation")
    key_metrics = models.TextField(help_text="Key metrics and validation data")
    customer_segments = models.TextField(help_text="Customer segments and market size")
    twelve_month_plan = models.TextField(help_text="12-month execution plan")

    # ——— Status & Admin Fields ———
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    review_feedback = models.TextField(
        blank=True, null=True,
        help_text="Admin feedback when sending back for review or rejecting"
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="piga_reviewed"
    )

    # ——— Remarks (chat-like, same pattern as ServiceRequest) ———
    remark = models.TextField(blank=True, null=True)

    # ——— Timestamps ———
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["status", "submitted_at"]),
            models.Index(fields=["applicant", "status"]),
        ]

    def __str__(self):
        return f"PIGA: {self.project_title} by {self.full_name} ({self.status})"

    def can_be_edited(self):
        """User can only edit when PENDING or REVIEW_BACK"""
        return self.status in ["PENDING", "REVIEW_BACK"]


# ——— Signal: Email notifications on create / status change ———
@receiver(post_save, sender=PigaApplication)
def handle_piga_status(sender, instance, created, **kwargs):
    from utils.util import send_notification_email

    if created:
        # Notify all superadmins / staff
        admins = User.objects.filter(is_staff=True).exclude(email="")
        for admin in admins:
            send_notification_email(
                recipient_email=admin.email,
                template_type="piga_new_admin",
                context={
                    "project_title": instance.project_title,
                    "applicant_name": instance.full_name,
                    "submitted_at": instance.submitted_at.strftime("%Y-%m-%d %H:%M") if instance.submitted_at else "Just now",
                },
            )

        # Confirmation to applicant
        if instance.applicant and instance.applicant.email:
            send_notification_email(
                recipient_email=instance.applicant.email,
                template_type="piga_submitted_user",
                context={
                    "project_title": instance.project_title,
                    "user_name": instance.full_name,
                },
            )
    else:
        # Status change → notify applicant
        if instance.applicant and instance.applicant.email:
            send_notification_email(
                recipient_email=instance.applicant.email,
                template_type="piga_status_update",
                context={
                    "project_title": instance.project_title,
                    "status": instance.get_status_display(),
                    "feedback": instance.review_feedback or "",
                },
            )
