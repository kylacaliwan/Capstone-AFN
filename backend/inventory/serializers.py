
from rest_framework import serializers
from .models import (
    InventoryCategory,
    InventoryItem,
    InventoryTransaction,
    InventoryReservation,
    ServiceTypeInventoryRequirement,
)


class InventoryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = '__all__'


class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    available_quantity = serializers.ReadOnlyField()
    is_low_stock = serializers.ReadOnlyField()
    
    class Meta:
        model = InventoryItem
        fields = '__all__'


class InventoryTransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    technician_name = serializers.CharField(source='technician.username', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.username', read_only=True)
    
    class Meta:
        model = InventoryTransaction
        fields = '__all__'


class InventoryReservationSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    technician_name = serializers.CharField(source='technician.username', read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        quantity = int(attrs.get('quantity', getattr(self.instance, 'quantity', 0)) or 0)
        if quantity <= 0:
            raise serializers.ValidationError({'quantity': 'Quantity must be greater than zero.'})

        item = attrs.get('item') or getattr(self.instance, 'item', None)
        status_value = attrs.get('status', getattr(self.instance, 'status', 'pending'))
        if item and status_value == 'pending':
            currently_reserved = getattr(self.instance, 'quantity', 0) if getattr(self.instance, 'status', 'pending') == 'pending' else 0
            if quantity > (item.available_quantity + currently_reserved):
                raise serializers.ValidationError({
                    'quantity': f'Only {item.available_quantity + currently_reserved} unit(s) are available for reservation.',
                })

        return attrs
    
    class Meta:
        model = InventoryReservation
        fields = '__all__'


class ServiceTypeInventoryRequirementSerializer(serializers.ModelSerializer):
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_sku = serializers.CharField(source='item.sku', read_only=True)
    available_quantity = serializers.IntegerField(source='item.available_quantity', read_only=True)

    def validate_quantity(self, value):
        if int(value) <= 0:
            raise serializers.ValidationError('Quantity must be greater than zero.')
        return value

    class Meta:
        model = ServiceTypeInventoryRequirement
        fields = '__all__'

