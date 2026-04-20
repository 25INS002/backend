from django.contrib import admin
from .models import Service, Availability, ServiceRequest, Payment


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "admin", "get_plan_names", "created_at"]
    search_fields = ["name", "description"]
    list_filter = ["created_at"]


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ["service", "day_of_week", "start_time", "end_time"]
    list_filter = ["day_of_week", "service"]


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ["service", "requested_by", "get_plan_name", "status", "requested_at"]
    list_filter = ["status", "requested_at"]
    search_fields = ["service__name", "requested_by__username"]
    readonly_fields = ["requested_at", "updated_at"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["razorpay_order_id", "razorpay_payment_id", "amount", "currency", "status", "created_at"]
    list_filter = ["status", "currency", "created_at"]
    search_fields = ["razorpay_order_id", "razorpay_payment_id"]
    readonly_fields = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature", "amount", "currency", "created_at", "updated_at"]
