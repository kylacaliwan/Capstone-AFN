from rest_framework import serializers
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source='message_text')
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    ticket_id = serializers.IntegerField(source='ticket.id', read_only=True)
    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    sender_phone = serializers.CharField(source='sender.phone', read_only=True)
    receiver_phone = serializers.CharField(source='receiver.phone', read_only=True)
    ticket_address = serializers.SerializerMethodField()
    ticket_latitude = serializers.SerializerMethodField()
    ticket_longitude = serializers.SerializerMethodField()

    def get_sender_name(self, obj):
        if not obj.sender:
            return ''
        full_name = obj.sender.get_full_name().strip()
        return full_name or obj.sender.username

    def get_receiver_name(self, obj):
        if not obj.receiver:
            return ''
        full_name = obj.receiver.get_full_name().strip()
        return full_name or obj.receiver.username

    def get_ticket_address(self, obj):
        try:
            return obj.ticket.request.location.address
        except Exception:
            return ''

    def get_ticket_latitude(self, obj):
        try:
            latitude = obj.ticket.request.location.latitude
            return float(latitude) if latitude is not None else None
        except Exception:
            return None

    def get_ticket_longitude(self, obj):
        try:
            longitude = obj.ticket.request.location.longitude
            return float(longitude) if longitude is not None else None
        except Exception:
            return None

    class Meta:
        model = Message
        fields = [
            'id',
            'ticket',
            'ticket_id',
            'ticket_address',
            'ticket_latitude',
            'ticket_longitude',
            'sender',
            'sender_name',
            'sender_phone',
            'receiver',
            'receiver_name',
            'receiver_phone',
            'text',
            'timestamp',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'ticket_id',
            'ticket_address',
            'ticket_latitude',
            'ticket_longitude',
            'sender',
            'sender_name',
            'sender_phone',
            'receiver_name',
            'receiver_phone',
            'timestamp',
            'created_at',
        ]
