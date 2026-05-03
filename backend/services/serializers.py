from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import serializers
from .models import (
    ServiceType, ServiceRequest, ServiceLocation, ServiceTicket,
    AfterSalesCase as FollowUpCase,
    TechnicianSkill, ServiceStatusHistory, InspectionChecklist, 
    TechnicianLocationHistory, ServiceAnalytics, TechnicianPerformance,
    DemandForecast, ServiceTrend
)
from .sla import (
    evaluate_service_request_sla,
    evaluate_service_ticket_sla,
    serialize_sla_evaluation,
)

class ServiceTypeSerializer(serializers.ModelSerializer):
    inventory_requirements_count = serializers.SerializerMethodField()

    def get_inventory_requirements_count(self, obj):
        return obj.inventory_requirements.count()

    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'description', 'estimated_duration', 'inventory_requirements_count']


class ServiceLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceLocation
        fields = '__all__'


class ServiceRequestSerializer(serializers.ModelSerializer):
    COORDINATE_QUANTIZER = Decimal('0.000001')

    location = ServiceLocationSerializer(read_only=True)
    client_name = serializers.CharField(source='client.username', read_only=True)
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    sla = serializers.SerializerMethodField()
    service = serializers.CharField(write_only=True, required=False, allow_blank=True)
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)
    lat = serializers.CharField(write_only=True, required=False, allow_blank=False)
    lng = serializers.CharField(write_only=True, required=False, allow_blank=False)
    locationDesc = serializers.CharField(write_only=True, required=False, allow_blank=True)
    location_address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    location_city = serializers.CharField(write_only=True, required=False, allow_blank=True)
    location_province = serializers.CharField(write_only=True, required=False, allow_blank=True)
    latitude = serializers.CharField(write_only=True, required=False, allow_blank=False)
    longitude = serializers.CharField(write_only=True, required=False, allow_blank=False)

    def _normalize_coordinate(self, value, *, field_name, minimum, maximum):
        if value in (None, ''):
            return None

        try:
            decimal_value = Decimal(str(value).strip())
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise serializers.ValidationError({field_name: 'Enter a valid coordinate.'}) from exc

        if decimal_value < Decimal(str(minimum)) or decimal_value > Decimal(str(maximum)):
            raise serializers.ValidationError({
                field_name: f'{field_name.replace("_", " ").capitalize()} must be between {minimum} and {maximum}.'
            })

        return decimal_value.quantize(self.COORDINATE_QUANTIZER, rounding=ROUND_HALF_UP)

    def _resolve_service_type(self, service_value):
        if service_value in (None, ''):
            return None

        service_value = str(service_value).strip()
        if not service_value:
            return None

        queryset = ServiceType.objects.all()
        if service_value.isdigit():
            try:
                return queryset.get(pk=int(service_value))
            except ServiceType.DoesNotExist as exc:
                raise serializers.ValidationError({'service_type': 'Selected service type does not exist.'}) from exc

        service_type = queryset.filter(name__iexact=service_value).first()
        if service_type:
            return service_type

        raise serializers.ValidationError({'service_type': 'Selected service type does not exist.'})

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        creating = self.instance is None

        if user and user.is_authenticated and user.role == 'client':
            attrs['client'] = user
        elif creating and not attrs.get('client'):
            raise serializers.ValidationError({'client': 'A client is required.'})

        if not attrs.get('service_type'):
            attrs['service_type'] = self._resolve_service_type(attrs.pop('service', None))
        else:
            attrs.pop('service', None)

        if creating and not attrs.get('service_type'):
            raise serializers.ValidationError({'service_type': 'A service type is required.'})

        description = attrs.get('description')
        if not description:
            description = attrs.pop('notes', '').strip()
            if description:
                attrs['description'] = description
        else:
            attrs.pop('notes', None)

        if creating and not attrs.get('description'):
            raise serializers.ValidationError({'description': 'A description is required.'})

        preferred_date = attrs.get(
            'preferred_date',
            getattr(self.instance, 'preferred_date', None),
        )
        preferred_time_slot = attrs.get(
            'preferred_time_slot',
            getattr(self.instance, 'preferred_time_slot', None),
        )

        if preferred_date and preferred_date < timezone.localdate():
            raise serializers.ValidationError({
                'preferred_date': 'Preferred appointment date cannot be in the past.',
            })
        if preferred_time_slot and not preferred_date:
            raise serializers.ValidationError({
                'preferred_date': 'Choose an appointment date when selecting a time slot.',
            })

        latitude = attrs.pop('latitude', None)
        longitude = attrs.pop('longitude', None)
        lat = attrs.pop('lat', None)
        lng = attrs.pop('lng', None)
        location_address = attrs.pop('location_address', '').strip()
        location_desc = attrs.pop('locationDesc', '').strip()
        location_city = attrs.pop('location_city', '').strip()
        location_province = attrs.pop('location_province', '').strip()

        latitude_field = 'latitude' if latitude is not None else 'lat'
        longitude_field = 'longitude' if longitude is not None else 'lng'
        latitude = latitude if latitude is not None else lat
        longitude = longitude if longitude is not None else lng

        latitude = self._normalize_coordinate(
            latitude,
            field_name=latitude_field,
            minimum=-90,
            maximum=90,
        )
        longitude = self._normalize_coordinate(
            longitude,
            field_name=longitude_field,
            minimum=-180,
            maximum=180,
        )

        location_address = location_address or location_desc
        has_location_input = any([
            location_address,
            location_city,
            location_province,
            latitude is not None,
            longitude is not None,
        ])

        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError({
                'latitude': 'Latitude and longitude must be provided together.',
                'longitude': 'Latitude and longitude must be provided together.',
            })

        if user and user.is_authenticated and user.role == 'client' and creating and not has_location_input:
            raise serializers.ValidationError({
                'location_address': 'A service location is required.',
                'latitude': 'A map location is required.',
                'longitude': 'A map location is required.',
            })

        if has_location_input:
            if not location_address:
                raise serializers.ValidationError({'location_address': 'A location note or address is required.'})
            if latitude is None or longitude is None:
                raise serializers.ValidationError({
                    'latitude': 'A map location is required.',
                    'longitude': 'A map location is required.',
                })

            attrs['location_payload'] = {
                'address': location_address,
                'city': location_city or 'Unspecified',
                'province': location_province or 'Unspecified',
                'latitude': latitude,
                'longitude': longitude,
            }

        return attrs

    def create(self, validated_data):
        location_payload = validated_data.pop('location_payload', None)
        request_obj = ServiceRequest.objects.create(**validated_data)
        if location_payload:
            ServiceLocation.objects.update_or_create(
                request=request_obj,
                defaults=location_payload,
            )
        return request_obj

    def update(self, instance, validated_data):
        location_payload = validated_data.pop('location_payload', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if location_payload:
            ServiceLocation.objects.update_or_create(
                request=instance,
                defaults=location_payload,
            )

        return instance

    def get_sla(self, obj):
        return serialize_sla_evaluation(evaluate_service_request_sla(obj))
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'client', 'client_name', 'service_type', 'service_type_name',
            'description', 'priority', 'status', 'preferred_date',
            'preferred_time_slot', 'scheduling_notes', 'request_date', 'updated_at',
            'auto_ticket_created', 'location', 'sla', 'service', 'notes', 'lat', 'lng',
            'locationDesc', 'location_address', 'location_city',
            'location_province', 'latitude', 'longitude'
        ]
        read_only_fields = ['request_date', 'updated_at', 'auto_ticket_created']
        extra_kwargs = {
            'client': {'required': False},
            'service_type': {'required': False},
            'description': {'required': False},
        }


class TechnicianSkillSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source='technician.username', read_only=True)
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    
    class Meta:
        model = TechnicianSkill
        fields = ['id', 'service_type', 'service_type_name', 'skill_level', 'technician_name', 'technician']
        read_only_fields = ['id', 'technician_name', 'technician']
    
    def validate(self, attrs):
        """Check for duplicate skills"""
        technician = self.context.get('request').user
        service_type = attrs.get('service_type')
        
        # If updating, allow same skill
        if self.instance:
            if self.instance.service_type == service_type and self.instance.technician == technician:
                return attrs
        
        # Check if this skill already exists for this technician
        if TechnicianSkill.objects.filter(technician=technician, service_type=service_type).exists():
            raise serializers.ValidationError(
                f"You already have this skill. Update the existing skill level instead."
            )
        
        return attrs


class ServiceStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = ServiceStatusHistory
        fields = '__all__'


class InspectionChecklistSerializer(serializers.ModelSerializer):
    completed_by_name = serializers.CharField(source='completed_by.username', read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        maintenance_required = attrs.get(
            'maintenance_required',
            getattr(self.instance, 'maintenance_required', False),
        )
        maintenance_profile = attrs.get(
            'maintenance_profile',
            getattr(self.instance, 'maintenance_profile', None),
        )
        maintenance_interval_days = attrs.get(
            'maintenance_interval_days',
            getattr(self.instance, 'maintenance_interval_days', None),
        )
        warranty_provided = attrs.get(
            'warranty_provided',
            getattr(self.instance, 'warranty_provided', False),
        )
        warranty_period_days = attrs.get(
            'warranty_period_days',
            getattr(self.instance, 'warranty_period_days', None),
        )
        proof_media = attrs.get(
            'proof_media',
            getattr(self.instance, 'proof_media', []),
        )
        follow_up_required = attrs.get(
            'follow_up_required',
            getattr(self.instance, 'follow_up_required', False),
        )
        follow_up_case_type = attrs.get(
            'follow_up_case_type',
            getattr(self.instance, 'follow_up_case_type', None),
        )
        follow_up_due_date = attrs.get(
            'follow_up_due_date',
            getattr(self.instance, 'follow_up_due_date', None),
        )
        follow_up_summary = attrs.get(
            'follow_up_summary',
            getattr(self.instance, 'follow_up_summary', None),
        )

        if maintenance_required and not maintenance_profile:
            raise serializers.ValidationError({
                'maintenance_profile': 'Select a maintenance profile when scheduled maintenance is required.',
            })

        if maintenance_interval_days is not None and int(maintenance_interval_days) <= 0:
            raise serializers.ValidationError({
                'maintenance_interval_days': 'Maintenance interval must be greater than zero.',
            })

        if warranty_provided and not warranty_period_days:
            raise serializers.ValidationError({
                'warranty_period_days': 'Provide a warranty period when warranty coverage is enabled.',
            })

        if warranty_period_days is not None and int(warranty_period_days) <= 0:
            raise serializers.ValidationError({
                'warranty_period_days': 'Warranty period must be greater than zero.',
            })

        if proof_media and not isinstance(proof_media, list):
            raise serializers.ValidationError({
                'proof_media': 'Proof media must be provided as a list.',
            })

        if follow_up_required and not follow_up_case_type:
            raise serializers.ValidationError({
                'follow_up_case_type': 'Select an after-sales case type when follow-up is required.',
            })

        if follow_up_required and not follow_up_summary:
            raise serializers.ValidationError({
                'follow_up_summary': 'Provide a short handoff summary for the after-sales team.',
            })

        if follow_up_case_type == 'maintenance':
            raise serializers.ValidationError({
                'follow_up_case_type': 'Use the maintenance section instead of creating a maintenance handoff here.',
            })

        if follow_up_case_type == 'warranty' and not warranty_provided:
            raise serializers.ValidationError({
                'follow_up_case_type': 'Warranty follow-up requires warranty coverage to be enabled first.',
            })

        if follow_up_due_date and follow_up_due_date < timezone.localdate():
            raise serializers.ValidationError({
                'follow_up_due_date': 'Follow-up due date cannot be in the past.',
            })

        return attrs
    
    class Meta:
        model = InspectionChecklist
        fields = '__all__'


class TechnicianLocationHistorySerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source='technician.username', read_only=True)
    
    class Meta:
        model = TechnicianLocationHistory
        fields = '__all__'


class ServiceTicketSerializer(serializers.ModelSerializer):
    request_details = ServiceRequestSerializer(source='request', read_only=True)
    technician_name = serializers.CharField(source='technician.username', read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.username', read_only=True)
    status_history = ServiceStatusHistorySerializer(many=True, read_only=True)
    inspection = InspectionChecklistSerializer(read_only=True)
    inventory_reservations = serializers.SerializerMethodField()
    crew_members = serializers.SerializerMethodField()
    sla = serializers.SerializerMethodField()

    def get_inventory_reservations(self, obj):
        return [
            {
                'id': reservation.id,
                'item_id': reservation.item_id,
                'item_name': reservation.item.name,
                'item_sku': reservation.item.sku,
                'quantity': reservation.quantity,
                'status': reservation.status,
                'required_date': reservation.required_date,
                'technician_id': reservation.technician_id,
                'technician_name': reservation.technician.username,
                'notes': reservation.notes,
            }
            for reservation in obj.inventory_reservations.select_related('item', 'technician').order_by('id')
        ]

    def get_crew_members(self, obj):
        return [
            {
                'id': assignment.technician_id,
                'username': assignment.technician.username,
                'name': assignment.technician.get_full_name().strip() or assignment.technician.username,
            }
            for assignment in obj.crew_assignments.select_related('technician').order_by('created_at', 'id')
        ]

    def get_sla(self, obj):
        return serialize_sla_evaluation(evaluate_service_ticket_sla(obj))
    
    class Meta:
        model = ServiceTicket
        fields = '__all__'
        read_only_fields = ['assigned_at', 'route_geometry', 'route_distance', 'route_duration']


class FollowUpCaseSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.username', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    service_type_name = serializers.CharField(source='service_ticket.request.service_type.name', read_only=True)
    service_address = serializers.SerializerMethodField()
    ticket_status = serializers.CharField(source='service_ticket.status', read_only=True)
    ticket_completed_date = serializers.DateTimeField(source='service_ticket.completed_date', read_only=True)
    ticket_warranty_status = serializers.CharField(source='service_ticket.warranty_status', read_only=True)
    ticket_warranty_end_date = serializers.DateField(source='service_ticket.warranty_end_date', read_only=True)
    creation_source_label = serializers.CharField(source='get_creation_source_display', read_only=True)

    def get_service_address(self, obj):
        try:
            return obj.service_ticket.request.location.address
        except ServiceLocation.DoesNotExist:
            return obj.client.address or None

    class Meta:
        model = FollowUpCase
        fields = '__all__'
        read_only_fields = ['client', 'created_by', 'resolved_at', 'created_at', 'updated_at', 'creation_source']


# Auto-assignment serializer
class AutoAssignSerializer(serializers.Serializer):
    """Serializer for auto-assignment request"""
    ticket_id = serializers.IntegerField()
    service_type_id = serializers.IntegerField()
    request_latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    request_longitude = serializers.DecimalField(max_digits=9, decimal_places=6)


# Analytics Serializers
class ServiceAnalyticsSerializer(serializers.ModelSerializer):
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    
    class Meta:
        model = ServiceAnalytics
        fields = [
            'id', 'date', 'service_type', 'service_type_name',
            'total_requests', 'completed_requests', 'pending_requests', 'cancelled_requests',
            'avg_response_time_hours', 'avg_completion_time_hours', 'technician_utilization_rate',
            'service_area_coverage', 'popular_locations', 'satisfaction_score', 'created_at'
        ]


class TechnicianPerformanceSerializer(serializers.ModelSerializer):
    technician_name = serializers.CharField(source='technician.username', read_only=True)
    
    class Meta:
        model = TechnicianPerformance
        fields = [
            'id', 'technician', 'technician_name', 'date',
            'tickets_assigned', 'tickets_completed', 'tickets_pending',
            'total_work_hours', 'avg_response_time_hours', 'avg_completion_time_hours',
            'customer_satisfaction', 'rework_rate', 'distance_traveled_km', 'fuel_efficiency',
            'created_at'
        ]


class DemandForecastSerializer(serializers.ModelSerializer):
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    
    class Meta:
        model = DemandForecast
        fields = [
            'id', 'service_type', 'service_type_name', 'forecast_date', 'forecast_period',
            'predicted_requests', 'confidence_level', 'weather_impact', 'seasonal_trend',
            'historical_average', 'actual_requests', 'forecast_accuracy', 'generated_at'
        ]


class ServiceTrendSerializer(serializers.ModelSerializer):
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    
    class Meta:
        model = ServiceTrend
        fields = [
            'id', 'service_type', 'service_type_name', 'trend_type', 'period_start', 'period_end',
            'average_requests', 'peak_day', 'peak_hour', 'growth_rate', 'trend_direction',
            'standard_deviation', 'confidence_interval', 'created_at'
        ]
