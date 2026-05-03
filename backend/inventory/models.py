
from django.db import models, transaction
from django.conf import settings


class InventoryCategory(models.Model):
    """Categories for inventory items"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Inventory Categories"
        ordering = ['name']


class InventoryItem(models.Model):
    """Main inventory items/equipment"""
    ITEM_TYPES = [
        ('equipment', 'Equipment'),
        ('part', 'Spare Part'),
        ('tool', 'Tool'),
        ('consumable', 'Consumable'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('reserved', 'Reserved'),
        ('out_of_stock', 'Out of Stock'),
        ('retired', 'Retired'),
    ]
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(InventoryCategory, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='equipment')
    
    # Quantities
    quantity = models.IntegerField(default=0)
    minimum_stock = models.IntegerField(default=5)
    reserved_quantity = models.IntegerField(default=0)
    
    # Location
    warehouse_location = models.CharField(max_length=100, blank=True, null=True)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Supplier
    supplier = models.CharField(max_length=200, blank=True, null=True)
    supplier_contact = models.TextField(blank=True, null=True)
    
    # Dates
    purchase_date = models.DateField(null=True, blank=True)
    warranty_expiry = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Low stock notification threshold (percentage)
    low_stock_threshold = models.IntegerField(default=40)  # 40% of minimum stock
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    # Notification tracking
    last_notification_sent = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    def save(self, *args, **kwargs):
        self.total_value = self.quantity * self.unit_price
        
        # Check if we need to send low stock notification
        old_item = None
        if self.pk:
            try:
                old_item = InventoryItem.objects.get(pk=self.pk)
            except InventoryItem.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Send notification if stock is low (40% or below minimum)
        self.check_and_notify_low_stock(old_item)
    
    def check_and_notify_low_stock(self, old_item=None):
        """Check if stock is below threshold and send notification"""
        threshold_value = (self.minimum_stock * self.low_stock_threshold) / 100
        
        # Check if stock is below threshold
        if self.available_quantity <= threshold_value:
            # Check if this is a new low stock situation or stock decreased
            should_notify = False
            
            if old_item is None:
                # New item - just created with low stock
                should_notify = True
            elif self.available_quantity < old_item.available_quantity:
                # Stock decreased
                should_notify = True
            
            if should_notify:
                self.send_low_stock_notification()
    
    def send_low_stock_notification(self):
        """Send low stock notification to admins"""
        from notifications.models import Notification
        from django.utils import timezone
        from .sms_utils import send_low_stock_alert
        
        # Calculate percentage
        if self.minimum_stock > 0:
            stock_percentage = (self.available_quantity / self.minimum_stock) * 100
        else:
            stock_percentage = 0
        
        # Create notification message
        if self.available_quantity == 0:
            message = f"URGENT: {self.name} (SKU: {self.sku}) is OUT OF STOCK!"
            notif_type = 'error'
        elif stock_percentage <= 20:
            message = f"CRITICAL: {self.name} (SKU: {self.sku}) - Only {self.available_quantity} units left ({stock_percentage:.0f}% of minimum)"
            notif_type = 'error'
        elif stock_percentage <= 40:
            message = f"Low Stock Alert: {self.name} (SKU: {self.sku}) - {self.available_quantity} units remaining ({stock_percentage:.0f}% of minimum)"
            notif_type = 'warning'
        else:
            return  # No notification needed
        
        # Notify all admins
        from users.models import User
        admins = User.objects.filter(role__in=['superadmin', 'admin'])
        
        for admin in admins:
            Notification.objects.get_or_create(
                user=admin,
                message=message,
                type=notif_type,
            )
        
        # Send SMS alert
        send_low_stock_alert(self)
        
        # Update last notification time without calling save() to avoid recursion
        InventoryItem.objects.filter(pk=self.pk).update(last_notification_sent=timezone.now())
    
    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    @property
    def is_low_stock(self):
        threshold_value = (self.minimum_stock * self.low_stock_threshold) / 100
        return self.available_quantity <= threshold_value


class InventoryTransaction(models.Model):
    """Track all inventory movements"""
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase/Receipt'),
        ('issue', 'Issue/Assignment'),
        ('return', 'Return'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Stock Adjustment'),
        ('reservation', 'Reservation'),
        ('cancellation', 'Reservation Cancellation'),
    ]
    
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    
    # Related to
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'technician'},
        related_name='inventory_transactions'
    )
    service_ticket = models.ForeignKey(
        'services.ServiceTicket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )
    
    # Transaction details
    reference_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    transaction_date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_inventory_transactions'
    )
    
    def __str__(self):
        return f"{self.transaction_type} - {self.item.name} - {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Wrap both saves in a transaction to prevent partial updates
        with transaction.atomic():
            # Snapshot old item state for notification comparison
            old_available = self.item.available_quantity

            # Update inventory quantities
            if self.transaction_type in ['purchase', 'return']:
                self.item.quantity += self.quantity
            elif self.transaction_type in ['issue', 'transfer']:
                self.item.quantity -= self.quantity
            elif self.transaction_type == 'reservation':
                self.item.reserved_quantity += self.quantity
            elif self.transaction_type == 'cancellation':
                self.item.reserved_quantity -= self.quantity
            elif self.transaction_type == 'adjustment':
                self.item.quantity = self.quantity  # Direct set

            # Save item first, then the transaction record
            self.item.save()
            super().save(*args, **kwargs)

        # Check and send low stock notification after transaction
        # Only notify if available quantity actually decreased
        if self.item.available_quantity < old_available:
            self.item.check_and_notify_low_stock()


class InventoryReservation(models.Model):
    """Reserve inventory items for future use"""
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='reservations')
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'technician'},
        related_name='inventory_reservations'
    )
    quantity = models.IntegerField()
    required_date = models.DateField()
    service_ticket = models.ForeignKey(
        'services.ServiceTicket',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_reservations'
    )
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')  # pending, fulfilled, cancelled
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reservation: {self.item.name} - {self.quantity} units"


class ServiceTypeInventoryRequirement(models.Model):
    """Default inventory requirements for a service type."""

    service_type = models.ForeignKey(
        'services.ServiceType',
        on_delete=models.CASCADE,
        related_name='inventory_requirements',
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='service_type_requirements',
    )
    quantity = models.PositiveIntegerField(default=1)
    auto_reserve = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['service_type__name', 'item__name']
        unique_together = ['service_type', 'item']

    def __str__(self):
        return f"{self.service_type.name}: {self.item.name} x{self.quantity}"

