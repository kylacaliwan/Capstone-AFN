from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'role', 'admin_scope', 'phone', 'address', 'status', 
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
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role = validated_data.get('role', 'client')

        # Validate requested role strictly
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if role not in valid_roles:
            role = 'client'

        request = self.context.get('request') if hasattr(self, 'context') else None
        is_request_admin = (
            request and
            getattr(request, 'user', None) and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )

        # Only admins can create elevated internal accounts.
        if role in ('admin', 'supervisor', 'follow_up', 'technician') and not is_request_admin:
            role = 'client'

        if role in ('admin', 'follow_up'):
            if not validated_data.get('admin_scope'):
                validated_data['admin_scope'] = 'service_follow_up' if role == 'follow_up' else 'general'

        validated_data['role'] = role

        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class UserUpdateSerializer(serializers.ModelSerializer):
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

        attrs['old_password'] = old_password
        return attrs
