from django.contrib import admin
from .models import Notification, NotificationTemplate, NotificationLog

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'status', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at', 'read_at']

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'subject']
    list_filter = ['notification_type']
    search_fields = ['name', 'subject']

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['notification', 'email_status', 'sms_status', 'last_attempt']
    list_filter = ['email_status', 'sms_status', 'last_attempt']
    readonly_fields = ['last_attempt']
