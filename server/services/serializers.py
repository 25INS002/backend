from rest_framework import serializers
from .models import Service, Availability, ServiceRequest, Payment
from django.contrib.auth.models import User


# ------------------ User ------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


# ------------------ Availability ------------------
class AvailabilitySerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(
        source="get_day_of_week_display", read_only=True
    )

    class Meta:
        model = Availability
        fields = ["id", "day_of_week", "day_of_week_display", "start_time", "end_time"]


class AvailabilityNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ["day_of_week", "start_time", "end_time"]

    def validate(self, data):
        if data["start_time"] >= data["end_time"]:
            raise serializers.ValidationError("End time must be after start time")
        return data


# ------------------ Service ------------------
class ServiceSerializer(serializers.ModelSerializer):
    availability_slots = AvailabilitySerializer(many=True, read_only=True)
    availability_slots_write = AvailabilityNestedSerializer(
        many=True, write_only=True, required=False, source="availability_slots"
    )

    admin = UserSerializer(read_only=True)
    admin_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="admin", write_only=True, required=False
    )

    available_plans = serializers.SerializerMethodField()
    plan_names = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "long_description",
            "media",
            "cost_discount",
            "admin",
            "admin_id",
            "created_at",
            "updated_at",
            "availability_slots",
            "availability_slots_write",
            "available_plans",
            "plan_names",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_available_plans(self, obj):
        return obj.get_available_plans()

    def get_plan_names(self, obj):
        return obj.get_plan_names()

    def create(self, validated_data):
        availability_data = validated_data.pop("availability_slots", [])
        user = self.context["request"].user

        # Superadmin can set/change admin
        if not getattr(user, "is_superadmin", False) and not user.is_superuser:
            validated_data["admin"] = user
        else:
            validated_data["admin"] = validated_data.get("admin", user)

        service = Service.objects.create(**validated_data)

        # Validate and create availability slots
        for slot_data in availability_data:
            slot = Availability(service=service, **slot_data)
            slot.clean()
            slot.save()

        return service

    def update(self, instance, validated_data):
        availability_data = validated_data.pop("availability_slots", None)
        user = self.context["request"].user

        # Normal admins cannot change admin
        if not getattr(user, "is_superadmin", False) and not user.is_superuser:
            validated_data.pop("admin", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if availability_data is not None:
            instance.availability_slots.all().delete()
            for slot_data in availability_data:
                slot = Availability(service=instance, **slot_data)
                slot.clean()
                slot.save()

        return instance


# ------------------ ServiceRequest ------------------
class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(), source="service", write_only=True
    )

    class Meta:
        model = ServiceRequest
        fields = ["service_id", "plan", "request_msg", "media_url"]

    def validate_plan(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Plan must be a dictionary")
        if "plan" not in value or "cost" not in value:
            raise serializers.ValidationError("Plan must contain 'plan' and 'cost'")
        cost = value.get("cost", 0)
        discount = value.get("discount", 0)
        if cost < 0 or discount < 0 or discount > cost:
            raise serializers.ValidationError("Invalid cost or discount")
        return value

    def validate_request_msg(self, value):
        if not isinstance(value, dict) or "subject" not in value or "body" not in value:
            raise serializers.ValidationError(
                "Request message must have 'subject' and 'body'"
            )
        return value

    def validate(self, data):
        service = data.get("service")
        plan_name = data.get("plan", {}).get("plan")
        if service and plan_name:
            available_plans = [
                plan.get("plan") for plan in service.cost_discount if "plan" in plan
            ]
            if plan_name not in available_plans:
                raise serializers.ValidationError(
                    {
                        "plan": f"Plan '{plan_name}' not available. Options: {', '.join(available_plans)}"
                    }
                )
        return data

    def create(self, validated_data):
        validated_data["requested_by"] = self.context["request"].user
        return super().create(validated_data)


class ServiceRequestSerializer(serializers.ModelSerializer):
    requested_by = UserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    final_price = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    payment_id = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "requested_by",
            "service",
            "plan",
            "status",
            "request_msg",
            "media_url",
            "remark",
            "requested_at",
            "updated_at",
            "final_price",
            "plan_name",
            "can_be_cancelled",
            "payment_status",
            "payment_id",
        ]
        read_only_fields = ["status", "remark", "requested_by"]

    def get_final_price(self, obj):
        return obj.get_final_price()

    def get_plan_name(self, obj):
        return obj.get_plan_name()

    def get_can_be_cancelled(self, obj):
        return obj.can_be_cancelled()

    def get_payment_status(self, obj):
        try:
            return obj.payment.status
        except Payment.DoesNotExist:
            return None

    def get_payment_id(self, obj):
        try:
            return obj.payment.razorpay_payment_id
        except Payment.DoesNotExist:
            return None


class ServiceRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = ["request_msg", "media_url", "remark"]

    def validate_request_msg(self, value):
        if not isinstance(value, dict) or "subject" not in value or "body" not in value:
            raise serializers.ValidationError(
                "Request message must have 'subject' and 'body'"
            )
        return value

    def validate_remark(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError("Remark must be a string")
        return value


class AdminServiceRequestUpdateSerializer(serializers.ModelSerializer):
    current_status = serializers.CharField(source="status", read_only=True)
    requested_by_info = UserSerializer(source="requested_by", read_only=True)
    service_info = ServiceSerializer(source="service", read_only=True)

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "status",
            "remark",
            "current_status",
            "requested_by_info",
            "service_info",
            "requested_at",
            "updated_at",
        ]

    def validate_status(self, value):
        instance = self.instance
        if (
            instance
            and instance.status in ["COMPLETED", "CANCELLED"]
            and value != instance.status
        ):
            raise serializers.ValidationError(
                f"Cannot change status from {instance.status}"
            )
        return value


class AvailabilityCheckSerializer(serializers.Serializer):
    day_of_week = serializers.ChoiceField(choices=Availability.DAY_CHOICES)
    time = serializers.TimeField()


class ServiceStatisticsSerializer(serializers.Serializer):
    total_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    completed_requests = serializers.IntegerField()
    popular_plans = serializers.ListField()


class ServiceListSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    plan_count = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "media",
            "admin_name",
            "plan_count",
            "created_at",
            "long_description",
            "cost_discount",
        ]

    def get_admin_name(self, obj):
        return obj.admin.get_full_name() if obj.admin else ""

    def get_plan_count(self, obj):
        return len(obj.cost_discount)


# ===================================================================
# PAYMENT SERIALIZERS — Razorpay Integration
# ===================================================================

class PaymentSerializer(serializers.ModelSerializer):
    amount_in_rupees = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id", "razorpay_order_id", "razorpay_payment_id",
            "amount", "amount_in_rupees", "currency", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_amount_in_rupees(self, obj):
        return obj.amount / 100


class CreateOrderSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    plan = serializers.DictField()
    request_msg = serializers.DictField()

    def validate_plan(self, value):
        if "plan" not in value or "cost" not in value:
            raise serializers.ValidationError("Plan must contain 'plan' and 'cost'")
        cost = value.get("cost", 0)
        discount = value.get("discount", 0)
        if cost < 0 or discount < 0 or discount > cost:
            raise serializers.ValidationError("Invalid cost or discount values")
        return value

    def validate_request_msg(self, value):
        if "subject" not in value or "body" not in value:
            raise serializers.ValidationError("Request message must have 'subject' and 'body'")
        return value

    def validate_service_id(self, value):
        if not Service.objects.filter(id=value).exists():
            raise serializers.ValidationError("Service not found")
        return value


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=256)
