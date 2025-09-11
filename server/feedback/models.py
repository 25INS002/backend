from django.db import models
from django.contrib.auth.models import User
from modules.models import Module  # assuming you already have the modules app

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="feedbacks")
    message = models.TextField()
    rating = models.IntegerField()  # e.g., 1–5 stars
    keywords = models.CharField(max_length=255, blank=True)  # comma-separated keywords
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="feedbacks")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback by {self.user.username} ({self.rating})"
