
from django.contrib import admin
from .models import (
    InventoryCategory,
    InventoryItem,
    InventoryTransaction,
    InventoryReservation,
    ServiceTypeInventoryRequirement,
)


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'description']
    search_fields = ['name', 'description']


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'quantity', 'available_quantity', 'status', 'unit_price']
    list_filter = ['status', 'category', 'item_type']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['total_value', 'created_at', 'updated_at']


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['item', 'transaction_type', 'quantity', 'technician', 'transaction_date']
    list_filter = ['transaction_type', 'transaction_date']
    search_fields = ['item__name', 'reference_number']
    readonly_fields = ['transaction_date']


@admin.register(InventoryReservation)
class InventoryReservationAdmin(admin.ModelAdmin):
    list_display = ['item', 'technician', 'quantity', 'required_date', 'status']
    list_filter = ['status', 'required_date']
    search_fields = ['item__name', 'technician__username']


@admin.register(ServiceTypeInventoryRequirement)
class ServiceTypeInventoryRequirementAdmin(admin.ModelAdmin):
    list_display = ['service_type', 'item', 'quantity', 'auto_reserve']
    list_filter = ['service_type', 'auto_reserve']
    search_fields = ['service_type__name', 'item__name', 'item__sku']

