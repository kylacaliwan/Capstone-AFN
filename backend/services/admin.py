from django.contrib import admin
from .models import (
    ServiceType, ServiceRequest, ServiceLocation, ServiceTicket, 
    TechnicianSkill, ServiceStatusHistory, InspectionChecklist,
    TechnicianLocationHistory
)

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'estimated_duration']
    search_fields = ['name']

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'service_type', 'priority', 'status', 'request_date']
    list_filter = ['status', 'priority', 'service_type']
    search_fields = ['client__username', 'description']

@admin.register(ServiceLocation)
class ServiceLocationAdmin(admin.ModelAdmin):
    list_display = ['request', 'address', 'city', 'province']
    search_fields = ['address', 'city']

@admin.register(ServiceTicket)
class ServiceTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'request', 'technician', 'supervisor', 'status', 'scheduled_date']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['request__id', 'technician__username']

@admin.register(TechnicianSkill)
class TechnicianSkillAdmin(admin.ModelAdmin):
    list_display = ['technician', 'service_type', 'skill_level']
    list_filter = ['skill_level', 'service_type']

@admin.register(ServiceStatusHistory)
class ServiceStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'status', 'changed_by', 'timestamp']
    list_filter = ['status', 'timestamp']

@admin.register(InspectionChecklist)
class InspectionChecklistAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'is_completed', 'recommendation', 'created_at', 'completed_at']
    list_filter = ['is_completed', 'recommendation']

@admin.register(TechnicianLocationHistory)
class TechnicianLocationHistoryAdmin(admin.ModelAdmin):
    list_display = ['technician', 'latitude', 'longitude', 'timestamp', 'accuracy']
    list_filter = ['timestamp', 'technician']
