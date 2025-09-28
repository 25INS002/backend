from rest_framework import serializers
from .models import Service, Availability, ServiceRequest
from django.contrib.auth.models import User

# Serializer for the User model, to be used in nested representations
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

# Serializer for the Availability model (for reading)
class AvailabilitySerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = Availability
        fields = ['id', 'day_of_week', 'day_of_week_display', 'start_time', 'end_time']

# Serializer for the Availability model (for writing)
class AvailabilityNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time']
    
    def validate(self, data):
        """
        Validate that end time is after start time
        """
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time")
        return data

# Serializer for the Service model
class ServiceSerializer(serializers.ModelSerializer):
    # For GET requests → read availability slots
    availability_slots = AvailabilitySerializer(many=True, read_only=True)

    # For GET requests → read admin info
    admin = UserSerializer(read_only=True)

    # For POST/PUT requests → accept nested availability slots
    availability_slots_write = AvailabilityNestedSerializer(
        many=True, write_only=True, required=False, source='availability_slots'
    )

    # Additional computed fields
    available_plans = serializers.SerializerMethodField()
    plan_names = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'long_description', 'media',
            'cost_discount', 'admin', 'created_at', 'updated_at',
            'availability_slots',        # read-only
            'availability_slots_write',  # write-only
            'available_plans',          # computed field
            'plan_names',               # computed field
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_available_plans(self, obj):
        """Return available plans with calculated prices"""
        return obj.get_available_plans()

    def get_plan_names(self, obj):
        """Return comma-separated plan names"""
        return obj.get_plan_names()

    def validate_cost_discount(self, value):
        """
        Validate the cost_discount JSON structure
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("cost_discount must be a list")
        
        for plan_data in value:
            if not isinstance(plan_data, dict):
                raise serializers.ValidationError("Each plan must be a dictionary")
            
            if 'plan' not in plan_data:
                raise serializers.ValidationError("Each plan must have a 'plan' field")
            
            if 'cost' not in plan_data:
                raise serializers.ValidationError("Each plan must have a 'cost' field")
            
            cost = plan_data.get('cost', 0)
            discount = plan_data.get('discount', 0)
            
            if not isinstance(cost, (int, float)) or cost < 0:
                raise serializers.ValidationError("Cost must be a positive number")
            
            if not isinstance(discount, (int, float)) or discount < 0:
                raise serializers.ValidationError("Discount must be a non-negative number")
            
            if discount > cost:
                raise serializers.ValidationError("Discount cannot be greater than cost")
        
        return value

    def create(self, validated_data):
        """
        Custom create method to handle the nested availability_slots.
        """
        # Extract availability data using the correct source name
        availability_data = validated_data.pop('availability_slots', [])
        
        # Get the current user from context
        user = self.context['request'].user
        validated_data['admin'] = user

        # Create the service
        service = Service.objects.create(**validated_data)

        # Create related availability slots
        for slot_data in availability_data:
            Availability.objects.create(service=service, **slot_data)

        return service

    def update(self, instance, validated_data):
        """
        Custom update method to handle nested availability_slots.
        """
        # Extract availability data using the correct source name
        availability_data = validated_data.pop('availability_slots', None)
        
        # Update service fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If availability_slots provided, replace existing ones
        if availability_data is not None:
            # Delete existing availability slots
            instance.availability_slots.all().delete()
            
            # Create new availability slots
            for slot_data in availability_data:
                Availability.objects.create(service=instance, **slot_data)

        return instance

# Serializer for creating ServiceRequest
class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='service',
        write_only=True
    )

    class Meta:
        model = ServiceRequest
        fields = [
            'service_id', 'plan', 'request_msg', 'media_url'
        ]

    def validate_plan(self, value):
        """
        Validate the plan structure
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Plan must be a dictionary")
        
        if 'plan' not in value:
            raise serializers.ValidationError("Plan must contain 'plan' field")
        
        if 'cost' not in value:
            raise serializers.ValidationError("Plan must contain 'cost' field")
        
        cost = value.get('cost', 0)
        discount = value.get('discount', 0)
        
        if not isinstance(cost, (int, float)) or cost < 0:
            raise serializers.ValidationError("Cost must be a positive number")
        
        if not isinstance(discount, (int, float)) or discount < 0:
            raise serializers.ValidationError("Discount must be a non-negative number")
        
        if discount > cost:
            raise serializers.ValidationError("Discount cannot be greater than cost")
        
        return value

    def validate_request_msg(self, value):
        """
        Validate the request_msg structure
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Request message must be a dictionary")
        
        if 'subject' not in value:
            raise serializers.ValidationError("Request message must contain 'subject' field")
        
        if 'body' not in value:
            raise serializers.ValidationError("Request message must contain 'body' field")
        
        return value

    def validate(self, data):
        """
        Validate that the selected plan exists in the service's available plans
        """
        service = data.get('service')
        plan_data = data.get('plan', {})
        plan_name = plan_data.get('plan')
        
        if service and plan_name:
            available_plans = [plan.get('plan') for plan in service.cost_discount]
            if plan_name not in available_plans:
                raise serializers.ValidationError({
                    'plan': f"Plan '{plan_name}' is not available for this service. Available plans: {', '.join(available_plans)}"
                })
        
        return data

    def create(self, validated_data):
        """
        Set the requested_by user automatically
        """
        validated_data['requested_by'] = self.context['request'].user
        return super().create(validated_data)

# Serializer for reading ServiceRequest
class ServiceRequestSerializer(serializers.ModelSerializer):
    # Read-only nested data
    requested_by = UserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    
    # Computed fields
    final_price = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'requested_by', 'service', 'plan', 'status', 
            'request_msg', 'media_url', 'remark', 'requested_at', 
            'updated_at', 'final_price', 'plan_name', 'can_be_cancelled'
        ]
        read_only_fields = ['status', 'remark', 'requested_by']

    def get_final_price(self, obj):
        """Calculate final price after discount"""
        return obj.get_final_price()

    def get_plan_name(self, obj):
        """Get plan name"""
        return obj.get_plan_name()

    def get_can_be_cancelled(self, obj):
        """Check if request can be cancelled"""
        return obj.can_be_cancelled()

# Serializer for updating ServiceRequest (user)
class ServiceRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = ['request_msg', 'media_url']
    
    def validate_request_msg(self, value):
        """
        Validate the request_msg structure
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Request message must be a dictionary")
        
        if 'subject' not in value:
            raise serializers.ValidationError("Request message must contain 'subject' field")
        
        if 'body' not in value:
            raise serializers.ValidationError("Request message must contain 'body' field")
        
        return value

# Serializer for Admins to update a ServiceRequest
class AdminServiceRequestUpdateSerializer(serializers.ModelSerializer):
    current_status = serializers.CharField(source='status', read_only=True)
    requested_by_info = UserSerializer(source='requested_by', read_only=True)
    service_info = ServiceSerializer(source='service', read_only=True)

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'status', 'remark', 'current_status', 
            'requested_by_info', 'service_info', 'requested_at', 'updated_at'
        ]

    def validate_status(self, value):
        """
        Validate status transitions
        """
        instance = self.instance
        if instance and instance.status == 'COMPLETED' and value != 'COMPLETED':
            raise serializers.ValidationError("Cannot change status from COMPLETED")
        
        if instance and instance.status == 'CANCELLED' and value != 'CANCELLED':
            raise serializers.ValidationError("Cannot change status from CANCELLED")
        
        return value

# Serializer for availability check
class AvailabilityCheckSerializer(serializers.Serializer):
    day_of_week = serializers.ChoiceField(choices=Availability.DAY_CHOICES)
    time = serializers.TimeField()

    def validate(self, data):
        """
        Validate that the time is in valid format
        """
        # Additional validation can be added here if needed
        return data

# Serializer for service statistics
class ServiceStatisticsSerializer(serializers.Serializer):
    total_requests = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    completed_requests = serializers.IntegerField()
    popular_plans = serializers.ListField()

# Nested serializer for service list view (lightweight)
class ServiceListSerializer(serializers.ModelSerializer):
    admin_name = serializers.CharField(source='admin.get_full_name', read_only=True)
    plan_count = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'media', 'admin_name', 
            'plan_count', 'created_at'
        ]

    def get_plan_count(self, obj):
        """Get number of available plans"""
        return len(obj.cost_discount)