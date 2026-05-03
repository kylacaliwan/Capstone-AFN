from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from .models import AdminSettings, User
from .rbac import (
    get_default_admin_scope_for_role,
    get_unknown_capability_codes,
    get_user_capability_codes,
    is_admin_scoped_role,
    is_superadmin_role,
)


class UserSerializer(serializers.ModelSerializer):
    capabilities = serializers.SerializerMethodField()

    def get_capabilities(self, obj):
        return sorted(get_user_capability_codes(obj))

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'role', 'admin_scope', 'phone', 'address', 'status',
                  'capabilities', 'is_active',
                  'current_latitude', 'current_longitude', 'is_available',
                  'last_location_update']
        read_only_fields = ['id', 'last_location_update']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 
                  'first_name', 'last_name', 'role', 'admin_scope', 'phone', 'address']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        try:
            validate_password(attrs['password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc

        requested_role = attrs.get('role', 'client')
        if requested_role == 'superadmin' and User.objects.filter(role='superadmin').exists():
            raise serializers.ValidationError({'role': 'Only one superadmin account is allowed.'})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role = validated_data.get('role', 'client')

        # Validate requested role strictly
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if role not in valid_roles:
            role = 'client'

        request = self.context.get('request') if hasattr(self, 'context') else None
        is_request_superadmin = (
            request and
            getattr(request, 'user', None) and
            request.user.is_authenticated and
            is_superadmin_role(request.user.role)
        )

        # Only the superadmin can create elevated internal accounts.
        if role in ('superadmin', 'admin', 'supervisor', 'follow_up', 'technician') and not is_request_superadmin:
            role = 'client'

        if is_admin_scoped_role(role) and not validated_data.get('admin_scope'):
            validated_data['admin_scope'] = get_default_admin_scope_for_role(role)

        validated_data['role'] = role

        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class UserUpdateSerializer(serializers.ModelSerializer):
    def validate_role(self, value):
        current_role = getattr(self.instance, 'role', None)
        if value == current_role:
            return value

        request = self.context.get('request') if hasattr(self, 'context') else None
        actor = getattr(request, 'user', None)

        if not actor or not actor.is_authenticated or not is_superadmin_role(getattr(actor, 'role', None)):
            raise serializers.ValidationError('Only the superadmin can change account roles.')

        if current_role == 'superadmin' and value != 'superadmin':
            raise serializers.ValidationError('The superadmin account cannot be demoted here.')

        if value == 'superadmin':
            existing_superadmin = User.objects.filter(role='superadmin')
            if getattr(self.instance, 'pk', None):
                existing_superadmin = existing_superadmin.exclude(pk=self.instance.pk)
            if existing_superadmin.exists():
                raise serializers.ValidationError('Only one superadmin account is allowed.')

        return value

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'phone', 'address',
            'role', 'admin_scope', 'status', 'current_latitude',
            'current_longitude', 'is_available'
        ]


class SelfUserUpdateSerializer(serializers.ModelSerializer):
    """Restricted serializer for self-service profile edits."""

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'address']

    def to_internal_value(self, data):
        allowed_fields = set(self.fields.keys())
        unexpected_fields = sorted(set(data.keys()) - allowed_fields)
        if unexpected_fields:
            raise serializers.ValidationError({
                field: 'This field cannot be updated on this endpoint.'
                for field in unexpected_fields
            })
        return super().to_internal_value(data)


class TechnicianLocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    accuracy = serializers.FloatField(required=False, default=0)


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=False, write_only=True)
    current_password = serializers.CharField(required=False, write_only=True)
    new_password = serializers.CharField(required=True)

    def validate(self, attrs):
        old_password = attrs.get('old_password') or attrs.get('current_password')
        if not old_password:
            raise serializers.ValidationError({'current_password': 'Current password is required'})

        user = self.context['request'].user
        if not user.check_password(old_password):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect'})

        try:
            validate_password(attrs['new_password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)}) from exc

        attrs['old_password'] = old_password
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True, trim_whitespace=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)
    password_confirm = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': "Password fields didn't match."})

        try:
            validate_password(attrs['new_password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)}) from exc

        return attrs


class AdminSettingsSerializer(serializers.ModelSerializer):
    systemName = serializers.CharField(source='system_name')
    supportEmail = serializers.EmailField(source='support_email')
    enableNotifications = serializers.BooleanField(source='enable_notifications')
    autoDispatchEnabled = serializers.BooleanField(source='auto_dispatch_enabled')
    smsNotificationsEnabled = serializers.BooleanField(source='sms_notifications_enabled')
    defaultTimeZone = serializers.CharField(source='default_time_zone')
    maxTechnicianAssignments = serializers.IntegerField(source='max_technician_assignments', min_value=1, max_value=50)

    class Meta:
        model = AdminSettings
        fields = [
            'systemName',
            'supportEmail',
            'enableNotifications',
            'autoDispatchEnabled',
            'smsNotificationsEnabled',
            'defaultTimeZone',
            'maxTechnicianAssignments',
        ]


class CapabilityGrantUpdateSerializer(serializers.Serializer):
    capabilities = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
    )

    def validate_capabilities(self, value):
        normalized_capabilities = []
        for capability_code in value:
            normalized_code = str(capability_code or '').strip()
            if normalized_code and normalized_code not in normalized_capabilities:
                normalized_capabilities.append(normalized_code)

        unknown_capabilities = get_unknown_capability_codes(normalized_capabilities)
        if unknown_capabilities:
            raise serializers.ValidationError(
                f"Unknown capability code(s): {', '.join(unknown_capabilities)}"
            )

        allowed_capabilities = set(self.context.get('allowed_capabilities') or [])
        disallowed_capabilities = sorted(set(normalized_capabilities) - allowed_capabilities)
        if disallowed_capabilities:
            raise serializers.ValidationError(
                f"You cannot assign capability code(s): {', '.join(disallowed_capabilities)}"
            )

        return normalized_capabilities


class CapabilityDefinitionSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    assignable = serializers.BooleanField()
