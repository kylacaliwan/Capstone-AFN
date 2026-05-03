from rest_framework import serializers
from .models import Notification, NotificationTemplate, NotificationLog, FirebaseToken


class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    related_ticket = serializers.IntegerField(source='ticket_id', read_only=True)
    related_request = serializers.IntegerField(source='request_id', read_only=True)
    priority = serializers.SerializerMethodField()
    push_sent = serializers.SerializerMethodField()

    def get_priority(self, obj):
        if obj.ticket_id and getattr(obj.ticket, 'priority', None):
            return obj.ticket.priority
        if obj.request_id and getattr(obj.request, 'priority', None):
            return obj.request.priority
        return None

    def get_push_sent(self, obj):
        return False

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'type', 'title', 'message',
            'ticket', 'request', 'related_ticket', 'related_request', 'status', 'priority',
            'send_email', 'send_sms',
            'email_sent', 'sms_sent', 'push_sent', 'created_at', 'read_at'
        ]
        read_only_fields = [
            'user', 'ticket', 'request', 'status',
            'created_at', 'read_at', 'email_sent', 'sms_sent',
            'push_sent', 'related_ticket', 'related_request', 'priority'
        ]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ['id', 'name', 'notification_type', 'subject', 'body', 'variables']


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'email_status', 'sms_status',
            'email_response', 'sms_response', 'attempt_count', 'last_attempt'
        ]


class FirebaseTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirebaseToken
        fields = ['id', 'fcm_token', 'device_name', 'device_type', 'is_active', 'created_at', 'last_used']
        read_only_fields = ['id', 'created_at', 'last_used']
