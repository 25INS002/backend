from django.contrib import admin
from .models import PigaApplication


@admin.register(PigaApplication)
class PigaApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "project_title",
        "full_name",
        "email",
        "organisation",
        "status",
        "submitted_at",
    ]
    list_filter = ["status", "submitted_at"]
    search_fields = ["project_title", "full_name", "email", "organisation"]
    readonly_fields = ["submitted_at", "updated_at"]
    ordering = ["-submitted_at"]
