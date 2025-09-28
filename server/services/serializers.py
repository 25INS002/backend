from rest_framework import serializers
from .models import Service, Availability, ServiceRequest
from django.contrib.auth.models import User

# Serializer for the User model, to be used in nested representations
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'email']


# Serializer for the Availability model (for reading)
class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['id', 'day_of_week', 'start_time', 'end_time']


# Serializer for the Availability model (for writing)
class AvailabilityNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time']


# Serializer for the Service model
class ServiceSerializer(serializers.ModelSerializer):
    # For GET requests → read availability slots
    availability_slots_read = AvailabilitySerializer(
        source='availability_slots', many=True, read_only=True
    )

    # For GET requests → read admin info
    admin = UserSerializer(read_only=True)

    # For POST/PUT requests → accept nested availability slots
    availability_slots = AvailabilityNestedSerializer(
        many=True, write_only=True, required=False
    )

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'description', 'long_description', 'media',
            'cost_discount', 'admin', 'created_at', 'updated_at',
            'availability_slots_read',  # read-only
            'availability_slots',       # write-only
        ]

    def create(self, validated_data):
        """
        Custom create method to handle the nested availability_slots.
        """
        # Extract availability data
        availability_data = validated_data.pop('availability_slots', [])

        # Create the service
        service = Service.objects.create(**validated_data)

        # Create related availability slots
        for slot_data in availability_data:
            Availability.objects.create(service=service, **slot_data)

        return service


# Serializer for the ServiceRequest model
class ServiceRequestSerializer(serializers.ModelSerializer):
    # Read-only nested data
    requested_by = UserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)

    # For POST → accept only service ID
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        source='service',
        write_only=True
    )

    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'requested_by', 'service', 'service_id',
            'plan', 'status', 'request_msg', 'media_url',
            'remark', 'requested_at', 'updated_at'
        ]
        read_only_fields = ['status', 'remark', 'requested_by']


# Serializer for Admins to update a ServiceRequest
class AdminServiceRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = ['status', 'remark']
