from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'ticket', 'created_at']
    list_filter = ['created_at', 'ticket']
    search_fields = ['sender__username', 'receiver__username', 'message_text']
    readonly_fields = ['created_at']
