from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@receiver(post_save, sender='inventory.InventoryItem')
def broadcast_inventory_update(sender, instance, created, **kwargs):
    """Broadcast inventory updates to all connected WebSocket clients"""
    try:
        from .serializers import InventoryItemSerializer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        serializer = InventoryItemSerializer(instance)

        # Send update to all clients in the inventory_updates group
        async_to_sync(channel_layer.group_send)(
            "inventory_updates",
            {
                "type": "inventory_update",
                "data": serializer.data
            }
        )

        # If item is low stock, also send low stock alert
        if instance.is_low_stock:
            async_to_sync(channel_layer.group_send)(
                "inventory_updates",
                {
                    "type": "low_stock_alert",
                    "data": serializer.data
                }
            )

    except Exception as e:
        # Log error but don't break the save operation
        print(f"Error broadcasting inventory update: {e}")
