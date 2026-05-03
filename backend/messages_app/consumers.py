import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Message
from services.models import ServiceTicket

logger = logging.getLogger(__name__)
User = get_user_model()


class MessageConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time messaging between technicians, admins, and clients.
    Enables instant message delivery without polling.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        user = self.scope['user']
        
        if not user.is_authenticated:
            await self.close()
            return
        
        # Create unique group name for user
        self.user_group_name = f'user_{user.id}'
        
        # Add this connection to the user's group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"User {user.username} ({user.id}) connected to WebSocket")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        user = self.scope['user']
        
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
        logger.info(f"User {user.username} ({user.id}) disconnected from WebSocket")

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages.
        Expected format: {
            "type": "send_message",
            "ticket_id": 123,
            "receiver_id": 456,
            "message_text": "Hello"
        }
        """
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'send_message':
                await self.handle_send_message(data)
            elif data.get('type') == 'typing':
                await self.handle_typing(data)
            else:
                await self.send_error('Invalid message type')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send_error(f'Error: {str(e)}')

    async def handle_send_message(self, data):
        """
        Process incoming message and save to database.
        Broadcast to both sender and receiver.
        """
        user = self.scope['user']
        
        try:
            ticket_id = data.get('ticket_id')
            receiver_id = data.get('receiver_id')
            message_text = data.get('message_text', '').strip()
            
            # Validate input
            if not ticket_id or not receiver_id or not message_text:
                await self.send_error('Missing required fields: ticket_id, receiver_id, message_text')
                return
            
            # Check permissions and save message
            message = await self.save_message(user.id, ticket_id, receiver_id, message_text)
            
            if message:
                # Prepare message data for broadcast
                message_data = {
                    'type': 'message',
                    'id': message['id'],
                    'senderId': message['sender_id'],
                    'senderName': message['sender_name'],
                    'receiverId': message['receiver_id'],
                    'receiverName': message['receiver_name'],
                    'ticketId': message['ticket_id'],
                    'messageText': message['message_text'],
                    'timestamp': message['timestamp'],
                }
                
                # Broadcast to both sender and receiver
                await self.channel_layer.group_send(
                    f'user_{user.id}',
                    {
                        'type': 'notify_message',
                        'message_data': message_data
                    }
                )
                
                if receiver_id != user.id:
                    await self.channel_layer.group_send(
                        f'user_{receiver_id}',
                        {
                            'type': 'notify_message',
                            'message_data': message_data
                        }
                    )
        except Exception as e:
            logger.error(f"Error handling send_message: {e}")
            await self.send_error(f'Failed to send message: {str(e)}')

    async def handle_typing(self, data):
        """
        Broadcast typing indicator to receiver.
        Format: {"type": "typing", "receiver_id": 456, "ticket_id": 123}
        """
        user = self.scope['user']
        receiver_id = data.get('receiver_id')
        
        if not receiver_id:
            return
        
        typing_data = {
            'type': 'typing_indicator',
            'sender_id': user.id,
            'sender_name': user.get_full_name() or user.username,
            'ticket_id': data.get('ticket_id')
        }
        
        await self.channel_layer.group_send(
            f'user_{receiver_id}',
            {
                'type': 'notify_typing',
                'typing_data': typing_data
            }
        )

    @database_sync_to_async
    def save_message(self, sender_id, ticket_id, receiver_id, message_text):
        """Save message to database with proper permissions."""
        try:
            sender = User.objects.get(id=sender_id)
            receiver = User.objects.get(id=receiver_id)
            ticket = ServiceTicket.objects.get(id=ticket_id)
            
            # Verify that sender/receiver have access to this ticket
            # Technician must be assigned or supervisor
            # Client must be the ticket's client
            # Admin can message anyone on a ticket
            if not self.has_permission(sender, ticket):
                logger.warning(
                    f"User {sender.username} attempted to message but lacks permission for ticket {ticket_id}"
                )
                return None
            
            message = Message.objects.create(
                ticket=ticket,
                sender=sender,
                receiver=receiver,
                message_text=message_text
            )
            
            return {
                'id': message.id,
                'sender_id': sender.id,
                'sender_name': sender.get_full_name() or sender.username,
                'receiver_id': receiver.id,
                'receiver_name': receiver.get_full_name() or receiver.username,
                'ticket_id': ticket.id,
                'message_text': message.message_text,
                'timestamp': message.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    def has_permission(self, user, ticket):
        """Check if user has permission to message about this ticket."""
        # Admins can always message
        if user.role in ('admin', 'superadmin'):
            return True
        
        # Technician can message if they're assigned or the supervisor
        if user.role == 'technician':
            return ticket.technician == user or ticket.supervisor == user
        
        # Client can message if they're the ticket's client
        if user.role == 'client':
            return ticket.request.client == user
        
        return False

    async def notify_message(self, event):
        """Send message notification to WebSocket."""
        message_data = event['message_data']
        
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': message_data
        }))

    async def notify_typing(self, event):
        """Send typing indicator to WebSocket."""
        typing_data = event['typing_data']
        
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'data': typing_data
        }))

    async def send_error(self, message):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
