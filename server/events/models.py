from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateTimeField() # event start date-time
    duration = models.DateTimeField() # event end date-time
    reg_end_date = models.DateTimeField(default=timezone.now) # event registeration end date-time
    description = models.TextField()
    long_description = models.TextField(blank=True)
    media = models.FileField(upload_to="events_media/", blank=True, null=True)
    participants = models.ManyToManyField(User, related_name="events_participated", blank=True)
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="events_created")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def media_url(self):
        if self.media:
            return self.media.url
        return None

    def __str__(self):
        return self.name
