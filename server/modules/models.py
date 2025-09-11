from django.db import models
from django.contrib.auth.models import User

class Module(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class AdminModuleAccess(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={"is_staff": True, "is_superuser": False})
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=True)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ("admin", "module")

    def __str__(self):
        return f"{self.admin.username} → {self.module.name}"
