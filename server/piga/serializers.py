from rest_framework import serializers
from .models import PigaApplication
from django.contrib.auth.models import User


# ——— Lightweight User serializer (same pattern as services) ———
class PigaUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


# ——— 1. CREATE serializer (user submits application) ———
class PigaApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PigaApplication
        fields = [
            "project_title",
            "date",
            "full_name",
            "email",
            "phone",
            "organisation",
            "elevator_pitch",
            "team",
            "problem_opportunity",
            "solution_technology",
            "current_status",
            "unique_value_proposition",
            "cost_budget",
            "key_metrics",
            "customer_segments",
            "twelve_month_plan",
        ]

    def create(self, validated_data):
        validated_data["applicant"] = self.context["request"].user
        return super().create(validated_data)


# ——— 2. READ serializer (full detail for listing/detail) ———
class PigaApplicationSerializer(serializers.ModelSerializer):
    applicant = PigaUserSerializer(read_only=True)
    reviewed_by = PigaUserSerializer(read_only=True)
    can_be_edited = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PigaApplication
        fields = [
            "id",
            "applicant",
            "project_title",
            "date",
            "full_name",
            "email",
            "phone",
            "organisation",
            "elevator_pitch",
            "team",
            "problem_opportunity",
            "solution_technology",
            "current_status",
            "unique_value_proposition",
            "cost_budget",
            "key_metrics",
            "customer_segments",
            "twelve_month_plan",
            "status",
            "status_display",
            "review_feedback",
            "reviewed_by",
            "remark",
            "submitted_at",
            "updated_at",
            "can_be_edited",
        ]
        read_only_fields = [
            "status",
            "review_feedback",
            "reviewed_by",
            "remark",
            "submitted_at",
            "updated_at",
        ]

    def get_can_be_edited(self, obj):
        return obj.can_be_edited()


# ——— 3. USER UPDATE serializer (only when PENDING or REVIEW_BACK) ———
class PigaApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PigaApplication
        fields = [
            "project_title",
            "date",
            "full_name",
            "email",
            "phone",
            "organisation",
            "elevator_pitch",
            "team",
            "problem_opportunity",
            "solution_technology",
            "current_status",
            "unique_value_proposition",
            "cost_budget",
            "key_metrics",
            "customer_segments",
            "twelve_month_plan",
        ]


# ——— 4. ADMIN UPDATE serializer (approve / reject / send back) ———
class PigaAdminUpdateSerializer(serializers.ModelSerializer):
    applicant_info = PigaUserSerializer(source="applicant", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PigaApplication
        fields = [
            "id",
            "status",
            "review_feedback",
            "remark",
            "applicant_info",
            "status_display",
            "submitted_at",
            "updated_at",
        ]

    def validate_status(self, value):
        valid_statuses = [s[0] for s in PigaApplication.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        instance = self.instance
        if instance and instance.status in ["APPROVED", "REJECTED"]:
            # Can't change from terminal states (optional strictness)
            if value not in ["APPROVED", "REJECTED", "UNDER_REVIEW"]:
                raise serializers.ValidationError(
                    f"Cannot change status from {instance.status} to {value}"
                )
        return value

    def update(self, instance, validated_data):
        # Set reviewed_by to the admin performing the action
        validated_data["reviewed_by"] = self.context["request"].user
        return super().update(instance, validated_data)


# ——— 5. LIST serializer (lightweight for tables/cards) ———
class PigaApplicationListSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PigaApplication
        fields = [
            "id",
            "project_title",
            "full_name",
            "email",
            "organisation",
            "status",
            "status_display",
            "submitted_at",
            "applicant_name",
        ]

    def get_applicant_name(self, obj):
        return obj.full_name or obj.applicant.get_full_name()
