from django.urls import path, include
from django.utils import timezone
from rest_framework import routers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from services.views_dashboard import DashboardView
from services.views import (
    TechnicianDashboardView, TechnicianJobsView, TechnicianScheduleView,
    TechnicianProfileView, TechnicianHistoryView, get_visible_service_tickets_queryset,
    normalize_proof_media_payload
)
from services.maintenance import MAINTENANCE_RULES, resolve_interval_days, sync_maintenance_schedule, sync_ticket_warranty
from users.models import User
from users.permissions import IsAdminOrSupervisor
from users.views import (
    AdminTechniciansViewSet, AdminClientsViewSet, AdminUsersViewSet,
    AdminSettingsViewSet, AdminServicesViewSet, AdminAnalyticsViewSet
)
from services.models import ServiceTicket, ServiceRequest, InspectionChecklist


def _display_name(user):
    if not user:
        return None
    full_name = user.get_full_name().strip()
    return full_name or user.username


@api_view(['GET'])
@permission_classes([IsAdminOrSupervisor])
def tracking_view(request):
    """Get technician and service request locations for tracking map"""
    # Get technician markers
    technicians = User.objects.filter(
        role='technician',
        status='active',
        current_latitude__isnull=False,
        current_longitude__isnull=False
    )
    
    tech_markers = []
    for tech in technicians:
        status_map = {True: 'available', False: 'on_job'}
        tech_markers.append({
            'id': tech.id,
            'name': _display_name(tech),
            'lat': float(tech.current_latitude),
            'lng': float(tech.current_longitude),
            'status': status_map.get(tech.is_available, 'offline')
        })
    
    # Get ticket markers for pending/assigned tickets
    ticket_markers = []
    tickets = get_visible_service_tickets_queryset(
        request.user,
        base_queryset=ServiceTicket.objects.filter(
            status__in=['Not Started', 'In Progress', 'On Hold']
        ).select_related('request__location', 'request__service_type', 'request__client')
    )
    
    for ticket in tickets:
        try:
            loc = ticket.request.location
            if loc and loc.latitude and loc.longitude:
                ticket_markers.append({
                    'id': ticket.id,
                    'client': _display_name(ticket.request.client) if ticket.request.client else 'Unknown',
                    'service': ticket.request.service_type.name if ticket.request.service_type else 'Service',
                    'lat': float(loc.latitude),
                    'lng': float(loc.longitude),
                    'locationDesc': loc.address or 'Service Location',
                    'status': ticket.status.lower().replace(' ', '_')
                })
        except:
            pass
    
    return Response({
        'techMarkers': tech_markers,
        'ticketMarkers': ticket_markers
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def checklist_view(request):
    """Compatibility endpoint for technician checklist submissions."""
    if request.user.role != 'technician':
        return Response({'error': 'Only technicians can submit checklists'}, status=403)

    ticket_id = request.data.get('jobId') or request.data.get('ticketId')
    if not ticket_id:
        return Response({'error': 'jobId is required'}, status=400)

    try:
        ticket = ServiceTicket.objects.get(id=ticket_id, technician=request.user)
    except ServiceTicket.DoesNotExist:
        return Response({'error': 'Ticket not found'}, status=404)

    completed = request.data.get('completed', {}) or {}
    notes = request.data.get('notes', '')
    photos = request.data.get('photos', []) or []
    videos = request.data.get('videos', []) or []
    proof_media = request.data.get('proof_media', []) or []
    all_complete = all(bool(value) for value in completed.values()) if completed else False
    maintenance_required = str(request.data.get('maintenance_required', '')).lower() in {'true', '1', 'yes'} if isinstance(request.data.get('maintenance_required'), str) else bool(request.data.get('maintenance_required'))
    maintenance_profile = request.data.get('maintenance_profile') or None
    maintenance_interval_days = request.data.get('maintenance_interval_days') or None
    maintenance_notes = request.data.get('maintenance_notes', '')
    warranty_provided = str(request.data.get('warranty_provided', '')).lower() in {'true', '1', 'yes'} if isinstance(request.data.get('warranty_provided'), str) else bool(request.data.get('warranty_provided'))
    warranty_period_days = request.data.get('warranty_period_days') or None
    warranty_notes = request.data.get('warranty_notes', '')

    if maintenance_required and not maintenance_profile:
        return Response({'maintenance_profile': 'Maintenance profile is required.'}, status=400)
    if maintenance_profile and maintenance_profile not in MAINTENANCE_RULES:
        return Response({'maintenance_profile': 'Unsupported maintenance profile.'}, status=400)

    if maintenance_interval_days not in (None, ''):
        try:
            maintenance_interval_days = int(maintenance_interval_days)
        except (TypeError, ValueError):
            return Response({'maintenance_interval_days': 'Maintenance interval must be a number.'}, status=400)
        if maintenance_interval_days <= 0:
            return Response({'maintenance_interval_days': 'Maintenance interval must be greater than zero.'}, status=400)
    elif maintenance_required and maintenance_profile:
        maintenance_interval_days = resolve_interval_days(maintenance_profile)

    if warranty_period_days not in (None, ''):
        try:
            warranty_period_days = int(warranty_period_days)
        except (TypeError, ValueError):
            return Response({'warranty_period_days': 'Warranty period must be a number.'}, status=400)
        if warranty_period_days <= 0:
            return Response({'warranty_period_days': 'Warranty period must be greater than zero.'}, status=400)
    elif warranty_provided:
        return Response({'warranty_period_days': 'Warranty period is required.'}, status=400)

    normalized_proof_media = normalize_proof_media_payload(
        photos=photos,
        videos=videos,
        media=proof_media,
    )

    checklist, _ = InspectionChecklist.objects.update_or_create(
        ticket=ticket,
        defaults={
            'is_completed': all_complete,
            'completed_at': timezone.now() if all_complete else None,
            'completed_by': request.user if all_complete else None,
            'site_accessible': all_complete,
            'electrical_available': all_complete,
            'electrical_adequate': all_complete,
            'safety_equipment_present': all_complete,
            'recommendation': 'Approved' if all_complete else 'Pending',
            'additional_notes': notes,
            'maintenance_required': maintenance_required,
            'maintenance_profile': maintenance_profile,
            'maintenance_interval_days': maintenance_interval_days,
            'maintenance_notes': maintenance_notes,
            'proof_media': normalized_proof_media,
            'warranty_provided': warranty_provided,
            'warranty_period_days': warranty_period_days,
            'warranty_notes': warranty_notes,
        }
    )
    sync_ticket_warranty(ticket)
    if ticket.status == 'Completed':
        sync_maintenance_schedule(ticket)
    return Response({'status': 'Checklist submitted', 'checklist_id': checklist.id})


# Admin router
admin_router = routers.DefaultRouter()
admin_router.register(r'technicians', AdminTechniciansViewSet, basename='admin-technicians')
admin_router.register(r'clients', AdminClientsViewSet, basename='admin-clients')
admin_router.register(r'users', AdminUsersViewSet, basename='admin-users')
admin_router.register(r'settings', AdminSettingsViewSet, basename='admin-settings')
admin_router.register(r'services', AdminServicesViewSet, basename='admin-services')
admin_router.register(r'analytics', AdminAnalyticsViewSet, basename='admin-analytics')

urlpatterns = [
    path('tracking', tracking_view, name='tracking'),
    path('users/', include('users.urls')),
    path('services/', include('services.urls')),
    # path('progress/', include('progress.urls')),  # Temporarily disabled
    path('messages/', include('messages_app.urls')),  # RE-ENABLED for ClientMessages
    path('notifications/', include('notifications.urls')),
    # path('history/', include('history.urls')),  # Temporarily disabled
    # path('forecast/', include('forecast.urls')),  # Temporarily disabled
    path('inventory/', include('inventory.urls')),
    path('dashboard/stats/', DashboardView.as_view(), name='dashboard-stats'),
    path('technician/dashboard/', TechnicianDashboardView.as_view({'get': 'dashboard'}), name='technician-dashboard'),
    path('technician/jobs/', TechnicianJobsView.as_view({'get': 'list'}), name='technician-jobs'),
    path('technician/jobs/<int:pk>/status/', TechnicianJobsView.as_view({'post': 'update_status'}), name='technician-job-status'),
    path('technician/schedule/', TechnicianScheduleView.as_view({'get': 'list'}), name='technician-schedule'),
    path('technician/profile/', TechnicianProfileView.as_view({'get': 'list', 'put': 'update'}), name='technician-profile'),
    path('technician/history/', TechnicianHistoryView.as_view({'get': 'list'}), name='technician-history'),
    path('checklist/', checklist_view, name='checklist-create'),
    path('admin/settings/', AdminSettingsViewSet.as_view({'get': 'list', 'put': 'update'}), name='admin-settings-root'),
    path('admin/', include(admin_router.urls)),
]
