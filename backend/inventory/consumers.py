import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from .models import InventoryItem
from .serializers import InventoryItemSerializer


class InventoryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "inventory_updates",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "inventory_updates",
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'get_inventory':
            await self.send_inventory_data()
        elif action == 'subscribe_low_stock':
            await self.send_low_stock_alerts()

    async def send_inventory_data(self):
        """Send current inventory data to client"""
        inventory_data = await self.get_inventory_data()
        await self.send(text_data=json.dumps({
            'type': 'inventory_data',
            'data': inventory_data
        }, cls=DjangoJSONEncoder))

    async def send_low_stock_alerts(self):
        """Send low stock alerts to client"""
        low_stock_data = await self.get_low_stock_data()
        await self.send(text_data=json.dumps({
            'type': 'low_stock_alerts',
            'data': low_stock_data
        }, cls=DjangoJSONEncoder))

    @database_sync_to_async
    def get_inventory_data(self):
        """Get all inventory items with their current status"""
        items = InventoryItem.objects.all()
        serializer = InventoryItemSerializer(items, many=True)
        return serializer.data

    @database_sync_to_async
    def get_low_stock_data(self):
        """Get items that are currently low on stock"""
        low_stock_items = InventoryItem.objects.filter(
            models.Q(available_quantity__lte=models.F('minimum_stock') * 0.4)
        )
        serializer = InventoryItemSerializer(low_stock_items, many=True)
        return serializer.data

    async def inventory_update(self, event):
        """Handle inventory update events"""
        await self.send(text_data=json.dumps({
            'type': 'inventory_update',
            'data': event['data']
        }, cls=DjangoJSONEncoder))

    async def low_stock_alert(self, event):
        """Handle low stock alert events"""
        await self.send(text_data=json.dumps({
            'type': 'low_stock_alert',
            'data': event['data']
        }, cls=DjangoJSONEncoder))