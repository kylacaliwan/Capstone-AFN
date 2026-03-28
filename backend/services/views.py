from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg, F
from django.core.mail import send_mail
from django.conf import settings
from datetime import time
import math
import logging

logger = logging.getLogger(__name__)

from .models import (
    ServiceType, ServiceRequest, ServiceLocation, ServiceTicket,
    TechnicianSkill, ServiceStatusHistory, InspectionChecklist,
    TechnicianLocationHistory, ServiceAnalytics, TechnicianPerformance,
    DemandForecast, ServiceTrend
)
from .maintenance import sync_maintenance_schedule, sync_ticket_warranty
from .serializers import (
    ServiceTypeSerializer, ServiceRequestSerializer, ServiceLocationSerializer,
    ServiceTicketSerializer, TechnicianSkillSerializer,
    ServiceStatusHistorySerializer, InspectionChecklistSerializer,
    TechnicianLocationHistorySerializer, AutoAssignSerializer,
    ServiceAnalyticsSerializer, TechnicianPerformanceSerializer,
    DemandForecastSerializer, ServiceTrendSerializer
)
from users.models import User
from users.serializers import SelfUserUpdateSerializer
from users.permissions import (
    IsAdmin, IsSupervisor, IsTechnician, IsClient,
    IsAdminOrSupervisor, IsAdminOrSupervisorOrTechnician,
    CanViewService, CanManageInventory
)
from inventory.automation import (
    issue_ticket_reservations,
    release_ticket_reservations,
    serialize_ticket_inventory,
    sync_ticket_reservations,
)

ACTIVE_TICKET_STATUSES = ['Not Started', 'In Progress', 'On Hold']
TICKET_REQUEST_STATUS_MAP = {
    'Not Started': 'Approved',
    'In Progress': 'In Progress',
    'On Hold': 'In Progress',
    'Completed': 'Completed',
    'Cancelled': 'Cancelled',
}
ALLOWED_TICKET_TRANSITIONS = {
    'Not Started': {'In Progress', 'Cancelled'},
    'In Progress': {'On Hold', 'Completed', 'Cancelled'},
    'On Hold': {'In Progress', 'Cancelled'},
    'Completed': set(),
    'Cancelled': set(),
}
ASSIGNABLE_TICKET_STATUSES = {'Not Started', 'On Hold'}
CLIENT_RESCHEDULABLE_TICKET_STATUSES = {'Not Started'}
CONTACTABLE_TICKET_STATUSES = {'Not Started', 'In Progress', 'On Hold'}
PARTS_REQUEST_TICKET_STATUSES = {'In Progress'}
TIME_SLOT_TO_TIME = {
    'morning': time(hour=9, minute=0),
    'midday': time(hour=12, minute=0),
    'afternoon': time(hour=15, minute=0),
    'evening': time(hour=18, minute=0),
}
SKILL_LEVEL_WEIGHTS = {
    'expert': 1.0,
    'intermediate': 0.75,
    'beginner': 0.5,
}


def send_notification_email(user, subject, message):
    """Helper function to send email notifications"""
    if user.email:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.warning(f"Email notification failed for user {user.id} ({user.email}): {e}")


def create_notification(user, message, notification_type='info'):
    """Helper to create in-app notifications"""
    from notifications.models import Notification
    Notification.objects.create(
        user=user,
        message=message,
        type=notification_type
    )


def sync_ticket_maintenance_schedule(ticket):
    """Refresh post-service lifecycle data without blocking ticket flow."""
    try:
        sync_ticket_warranty(ticket)
        if ticket.status == 'Completed':
            sync_maintenance_schedule(ticket)
    except Exception as exc:
        logger.warning(
            "Post-service lifecycle sync failed for ticket %s: %s",
            getattr(ticket, 'id', 'unknown'),
            exc,
        )


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lon = math.radians(float(lon2) - float(lon1))
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def normalize_time_slot(value):
    if value in [None, '']:
        return None
    value = str(value).strip().lower()
    if value in TIME_SLOT_TO_TIME:
        return value
    return None


def get_default_time_for_slot(time_slot):
    return TIME_SLOT_TO_TIME.get(normalize_time_slot(time_slot))


def apply_schedule_fields(ticket, *, scheduled_date=None, scheduled_time=None, scheduled_time_slot=None):
    if scheduled_date is not None:
        ticket.scheduled_date = scheduled_date

    if scheduled_time_slot is not None:
        ticket.scheduled_time_slot = normalize_time_slot(scheduled_time_slot)

    if scheduled_time is not None:
        ticket.scheduled_time = scheduled_time
    elif scheduled_time_slot is not None:
        ticket.scheduled_time = get_default_time_for_slot(scheduled_time_slot)

    return ticket


def build_initial_ticket_payload(request_obj):
    preferred_time_slot = normalize_time_slot(request_obj.preferred_time_slot)
    return {
        'scheduled_date': request_obj.preferred_date or timezone.localdate(),
        'scheduled_time_slot': preferred_time_slot,
        'scheduled_time': get_default_time_for_slot(preferred_time_slot),
        'status': 'Not Started',
        'notes': request_obj.scheduling_notes or None,
    }


def normalize_proof_media_payload(*, photos=None, videos=None, media=None):
    normalized_media = []

    for item in media or []:
        if isinstance(item, dict):
            media_type = str(item.get('type') or 'photo').strip().lower()
            normalized_media.append({
                'type': 'video' if media_type == 'video' else 'photo',
                'name': str(item.get('name') or item.get('url') or f'{media_type}-proof').strip(),
                'url': str(item.get('url') or item.get('name') or '').strip(),
            })
        else:
            value = str(item).strip()
            if value:
                normalized_media.append({'type': 'photo', 'name': value, 'url': value})

    for entry in photos or []:
        value = str(entry).strip()
        if value:
            normalized_media.append({'type': 'photo', 'name': value, 'url': value})

    for entry in videos or []:
        value = str(entry).strip()
        if value:
            normalized_media.append({'type': 'video', 'name': value, 'url': value})

    return normalized_media


def score_technician_fit(ticket, technician, request_lat, request_lon):
    if technician.current_latitude is None or technician.current_longitude is None:
        return None

    skill = TechnicianSkill.objects.filter(
        technician=technician,
        service_type=ticket.request.service_type,
    ).first()
    if not skill:
        return None

    distance_km = calculate_distance(
        request_lat,
        request_lon,
        technician.current_latitude,
        technician.current_longitude,
    )
    active_load = ServiceTicket.objects.filter(
        technician=technician,
        status__in=ACTIVE_TICKET_STATUSES,
    ).exclude(pk=ticket.pk).count()
    same_day_load = ServiceTicket.objects.filter(
        technician=technician,
        scheduled_date=ticket.scheduled_date,
        status__in=['Not Started', 'In Progress', 'On Hold', 'Completed'],
    ).exclude(pk=ticket.pk).count()

    score = 0.0
    score += SKILL_LEVEL_WEIGHTS.get(skill.skill_level, 0.4) * 45
    score += max(0, 30 - (distance_km * 2.5))
    score += max(0, 15 - (active_load * 5))
    score += max(0, 10 - (same_day_load * 3))
    if technician.is_available:
        score += 5

    summary = (
        f"{skill.get_skill_level_display()} skill, {distance_km:.1f} km away, "
        f"{active_load} active job(s), {same_day_load} job(s) on this date."
    )
    return {
        'score': round(score, 2),
        'distance_km': round(distance_km, 2),
        'skill_level': skill.skill_level,
        'summary': summary,
    }


def get_visible_service_requests_queryset(user, base_queryset=None, include_follow_up=False):
    if base_queryset is None:
        base_queryset = ServiceRequest.objects.select_related('client', 'location', 'service_type')

    if user.role in ['admin', 'supervisor']:
        return base_queryset
    if user.role == 'client':
        return base_queryset.filter(client=user)
    if user.role == 'technician':
        assigned_request_ids = ServiceTicket.objects.filter(technician=user).values_list('request_id', flat=True)
        return base_queryset.filter(id__in=assigned_request_ids)
    if include_follow_up and user.role == 'follow_up':
        completed_request_ids = ServiceTicket.objects.filter(status='Completed').values_list('request_id', flat=True)
        return base_queryset.filter(id__in=completed_request_ids)
    return base_queryset.none()


def get_visible_service_tickets_queryset(user, base_queryset=None):
    if base_queryset is None:
        base_queryset = ServiceTicket.objects.select_related(
            'technician', 'request__service_type', 'request__client', 'request__location'
        )

    if user.role == 'admin':
        return base_queryset
    if user.role == 'follow_up':
        return base_queryset.filter(status='Completed')
    if user.role == 'supervisor':
        return base_queryset.filter(supervisor=user)
    if user.role == 'technician':
        return base_queryset.filter(technician=user)
    if user.role == 'client':
        return base_queryset.filter(request__client=user)
    return base_queryset.none()


def sync_technician_availability(technician, *, force_available=False):
    if not technician or technician.role != 'technician':
        return

    if force_available:
        desired_availability = True
    else:
        has_active_tickets = ServiceTicket.objects.filter(
            technician=technician,
            status__in=ACTIVE_TICKET_STATUSES,
        ).exists()
        desired_availability = not has_active_tickets

    if technician.is_available != desired_availability:
        technician.is_available = desired_availability
        technician.save(update_fields=['is_available'])


def normalize_ticket_status(value):
    if value in [None, '']:
        return None

    aliases = {}
    for status_value, _label in ServiceTicket.STATUS_CHOICES:
        aliases[status_value.lower()] = status_value
        aliases[status_value.lower().replace(' ', '_')] = status_value

    return aliases.get(str(value).strip().lower())


def clear_reschedule_request(ticket):
    ticket.reschedule_requested = False
    ticket.reschedule_reason = None
    ticket.reschedule_requested_at = None


def sync_request_status_from_ticket(ticket):
    mapped_status = TICKET_REQUEST_STATUS_MAP.get(ticket.status)
    request_obj = ticket.request
    if mapped_status and request_obj.status != mapped_status:
        request_obj.status = mapped_status
        request_obj.save(update_fields=['status', 'updated_at'])


def validate_ticket_transition(ticket, new_status, *, allow_same=False):
    normalized_status = normalize_ticket_status(new_status)
    if not normalized_status:
        raise ValueError('Unsupported ticket status.')

    if normalized_status == ticket.status:
        if allow_same:
            return normalized_status
        raise ValueError(f'Ticket is already {normalized_status}.')

    allowed_statuses = ALLOWED_TICKET_TRANSITIONS.get(ticket.status, set())
    if normalized_status not in allowed_statuses:
        raise ValueError(f'Cannot move ticket from {ticket.status} to {normalized_status}.')

    return normalized_status


def apply_ticket_status_change(ticket, new_status, *, changed_by, notes=''):
    normalized_status = validate_ticket_transition(ticket, new_status)
    now = timezone.now()
    update_fields = ['status', 'updated_at']

    ticket.status = normalized_status

    if normalized_status == 'In Progress':
        if not ticket.start_time:
            ticket.start_time = now
            update_fields.append('start_time')
        clear_reschedule_request(ticket)
        update_fields.extend(['reschedule_requested', 'reschedule_reason', 'reschedule_requested_at'])
    elif normalized_status == 'Completed':
        if not ticket.start_time:
            ticket.start_time = now
            update_fields.append('start_time')
        ticket.end_time = now
        ticket.completed_date = now
        clear_reschedule_request(ticket)
        update_fields.extend([
            'end_time',
            'completed_date',
            'reschedule_requested',
            'reschedule_reason',
            'reschedule_requested_at',
        ])
    elif normalized_status == 'Cancelled':
        clear_reschedule_request(ticket)
        update_fields.extend(['reschedule_requested', 'reschedule_reason', 'reschedule_requested_at'])

    ticket.save(update_fields=list(dict.fromkeys(update_fields)))
    sync_request_status_from_ticket(ticket)
    sync_technician_availability(ticket.technician)

    if normalized_status == 'Completed':
        issue_ticket_reservations(
            ticket,
            performed_by=changed_by,
            reason=f'Issued automatically when ticket #{ticket.id} was completed.',
        )
        sync_ticket_maintenance_schedule(ticket)
    elif normalized_status == 'Cancelled':
        release_ticket_reservations(
            ticket,
            performed_by=changed_by,
            reason=f'Released automatically when ticket #{ticket.id} was cancelled.',
        )

    ServiceStatusHistory.objects.create(
        ticket=ticket,
        status=normalized_status,
        changed_by=changed_by,
        notes=notes,
    )

    return normalized_status


class ServiceTypeViewSet(viewsets.ModelViewSet):
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    
    def get_permissions(self):
        """Allow anyone to read service types (no auth required), but only admins/supervisors can create/update/delete"""
        if self.action in ['list', 'retrieve']:
            return []  # No permission required to view service types
        return [IsAdminOrSupervisor()]  # Only admin/supervisor can create/update/delete


class ServiceRequestViewSet(viewsets.ModelViewSet):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]  # Any authenticated user can create requests
        elif self.action in ['update', 'partial_update', 'destroy', 'approve', 'reject']:
            return [IsAdminOrSupervisor()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Filter queryset based on user role"""
        return get_visible_service_requests_queryset(self.request.user)
    
    def perform_create(self, serializer):
        with transaction.atomic():
            request_obj = serializer.save()

            # Auto-approve and create ticket for immediate admin visibility (can be adjusted later)
            request_obj.status = 'Approved'
            request_obj.auto_ticket_created = True
            request_obj.save()

            ticket = ServiceTicket.objects.create(
                request=request_obj,
                **build_initial_ticket_payload(request_obj),
            )

            ServiceStatusHistory.objects.create(
                ticket=ticket,
                status='Not Started',
                changed_by=self.request.user,
                notes='Auto-created ticket from client request'
            )

        # Send notification to admin
        admins = User.objects.filter(role='admin')
        for admin in admins:
            create_notification(
                admin,
                f"New service request from {request_obj.client.username} (Ticket #{ticket.id})",
                'info'
            )
            send_notification_email(
                admin,
                'New Service Request Created',
                f"Service request #{request_obj.id} from {request_obj.client.username} was auto-approved and created as ticket #{ticket.id}."
            )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve request and optionally auto-create ticket"""
        service_request = self.get_object()
        if service_request.status in ['Cancelled', 'Completed']:
            return Response(
                {'error': f'Cannot approve a {service_request.status.lower()} request.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        service_request.status = 'Approved'
        service_request.save()
        
        # Auto-create ticket if enabled
        if not service_request.auto_ticket_created:
            ticket = ServiceTicket.objects.create(
                request=service_request,
                **build_initial_ticket_payload(service_request),
            )
            service_request.auto_ticket_created = True
            service_request.save()
            
            # Create initial status history
            ServiceStatusHistory.objects.create(
                ticket=ticket,
                status='Not Started',
                changed_by=request.user,
                notes='Ticket auto-created from approved request'
            )
            
            # Notify client
            create_notification(
                service_request.client,
                f"Your service request has been approved. Ticket #{ticket.id} created.",
                'success'
            )
            send_notification_email(
                service_request.client,
                'Service Request Approved',
                f'Your service request for {service_request.service_type.name} has been approved. Ticket #{ticket.id} has been created.'
            )
        
        return Response({'status': 'Request approved'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel the service request"""
        service_request = self.get_object()
        related_ticket = ServiceTicket.objects.filter(request=service_request).select_related('technician').first()

        if service_request.status == 'Completed':
            return Response(
                {'error': 'Completed requests cannot be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if related_ticket and related_ticket.status in ['In Progress', 'Completed']:
            return Response(
                {'error': f'Request cannot be cancelled while ticket #{related_ticket.id} is {related_ticket.status.lower()}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service_request.status = 'Cancelled'
        service_request.save(update_fields=['status', 'updated_at'])

        if related_ticket and related_ticket.status != 'Cancelled':
            related_ticket.status = 'Cancelled'
            clear_reschedule_request(related_ticket)
            related_ticket.save(update_fields=[
                'status',
                'reschedule_requested',
                'reschedule_reason',
                'reschedule_requested_at',
                'updated_at',
            ])
            sync_technician_availability(related_ticket.technician)
            release_ticket_reservations(
                related_ticket,
                performed_by=request.user,
                reason='Released because the parent service request was cancelled.',
            )
            ServiceStatusHistory.objects.create(
                ticket=related_ticket,
                status='Cancelled',
                changed_by=request.user,
                notes='Ticket cancelled because the parent service request was cancelled.'
            )
            if related_ticket.technician:
                create_notification(
                    related_ticket.technician,
                    f"Ticket #{related_ticket.id} was cancelled before work started.",
                    'warning'
                )
        
        create_notification(
            service_request.client,
            "Your service request has been cancelled.",
            'warning'
        )
        
        return Response({'status': 'Request cancelled'})


class ServiceLocationViewSet(viewsets.ModelViewSet):
    queryset = ServiceLocation.objects.select_related('request__client', 'request__service_type')
    serializer_class = ServiceLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrSupervisor()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        visible_requests = get_visible_service_requests_queryset(
            self.request.user,
            include_follow_up=True,
        )
        return self.queryset.filter(request__in=visible_requests)


class ServiceTicketViewSet(viewsets.ModelViewSet):
    queryset = ServiceTicket.objects.all()
    serializer_class = ServiceTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """Return appropriate permissions based on action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'assign', 'auto_assign', 'update_status', 'reschedule']:
            return [IsAdminOrSupervisor()]
        elif self.action in ['start_work', 'complete_work', 'add_progress', 'add_notes', 'upload_photos', 'request_parts', 'contact_client']:
            return [IsTechnician()]
        elif self.action in ['request_reschedule', 'submit_feedback']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Filter queryset based on user role"""
        return get_visible_service_tickets_queryset(self.request.user)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Unified assignment endpoint - replaces assign_technician and old assign.
        Accepts: technician_id (required), auto_assign (bool), calculate_route (bool)
        """
        ticket = self.get_object()
        technician_id = request.data.get('technician_id')

        if ticket.status not in ASSIGNABLE_TICKET_STATUSES:
            return Response(
                {'error': f'Only tickets in {" or ".join(sorted(ASSIGNABLE_TICKET_STATUSES))} can be assigned.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not technician_id:
            return Response({'error': 'technician_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            technician = User.objects.get(id=technician_id, role='technician')
            if technician.status != 'active':
                return Response({'error': 'Technician must be active before assignment.'}, status=status.HTTP_400_BAD_REQUEST)

            scheduled_date = None
            if request.data.get('scheduled_date'):
                scheduled_date = parse_date(str(request.data.get('scheduled_date')))
                if scheduled_date is None:
                    return Response({'error': 'scheduled_date must be a valid date'}, status=status.HTTP_400_BAD_REQUEST)

            scheduled_time = None
            if request.data.get('scheduled_time'):
                scheduled_time = parse_time(str(request.data.get('scheduled_time')))
                if scheduled_time is None:
                    return Response({'error': 'scheduled_time must be a valid time'}, status=status.HTTP_400_BAD_REQUEST)

            requested_time_slot = request.data.get('scheduled_time_slot')
            if requested_time_slot not in [None, ''] and normalize_time_slot(requested_time_slot) is None:
                return Response({'error': 'scheduled_time_slot must be a supported time slot'}, status=status.HTTP_400_BAD_REQUEST)

            previous_technician = ticket.technician
            ticket.technician = technician
            ticket.assigned_at = timezone.now()
            apply_schedule_fields(
                ticket,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                scheduled_time_slot=requested_time_slot,
            )
            ticket.smart_assignment_score = None
            ticket.smart_assignment_summary = None
            ticket.save()
            sync_technician_availability(technician)
            inventory_summary = sync_ticket_reservations(ticket, performed_by=request.user)

            if previous_technician and previous_technician != technician:
                sync_technician_availability(previous_technician)

            # Calculate routing information if coordinates available
            try:
                loc = ticket.request.location
                if loc.latitude and loc.longitude and technician.current_latitude and technician.current_longitude:
                    from .ors_utils import get_route
                    route = get_route(
                        (float(loc.longitude), float(loc.latitude)),
                        (float(technician.current_longitude), float(technician.current_latitude))
                    )
                    if route and 'features' in route and route['features']:
                        geom = route['features'][0].get('geometry')
                        props = route['features'][0].get('properties', {}).get('segments', [{}])[0]
                        ticket.route_geometry = geom
                        ticket.route_distance = props.get('distance')
                        ticket.route_duration = props.get('duration')
                        ticket.save()
            except Exception as e:
                logger.warning(f"Route calculation failed for ticket {ticket.id}: {e}")
            
            # Create status history
            ServiceStatusHistory.objects.create(
                ticket=ticket,
                status=ticket.status,
                changed_by=request.user,
                notes=f'Technician {technician.username} assigned'
            )
            
            # Notify technician
            create_notification(
                technician,
                f"You have been assigned to ticket #{ticket.id}",
                'info'
            )
            send_notification_email(
                technician,
                'New Ticket Assignment',
                f'You have been assigned to ticket #{ticket.id} for {ticket.request.service_type.name}'
            )
            create_notification(
                ticket.request.client,
                (
                    f"Your service ticket #{ticket.id} is now assigned to {technician.username}"
                    f"{f' for {ticket.scheduled_date}' if ticket.scheduled_date else ''}."
                ),
                'info'
            )
            
            return Response({
                'success': True,
                'message': 'Technician assigned',
                'ticket_id': ticket.id,
                'technician': {
                    'id': technician.id,
                    'username': technician.username
                },
                'route_distance': ticket.route_distance,
                'route_duration': ticket.route_duration,
                'inventory_summary': inventory_summary,
            })
        except User.DoesNotExist:
            return Response(
                {'error': 'Technician not found', 'success': False},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def auto_assign(self, request, pk=None):
        """Auto-assign the best available technician using skill, distance, and workload."""
        ticket = self.get_object()
        service_type = ticket.request.service_type

        if ticket.status not in ASSIGNABLE_TICKET_STATUSES:
            return Response(
                {'error': f'Only tickets in {" or ".join(sorted(ASSIGNABLE_TICKET_STATUSES))} can be auto-assigned.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get location of the service request
        try:
            location = ticket.request.location
            request_lat = location.latitude
            request_lon = location.longitude
        except ServiceLocation.DoesNotExist:
            return Response({'error': 'Service location not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find technicians with the required skill
        skilled_technicians = TechnicianSkill.objects.filter(
            service_type=service_type
        ).values_list('technician_id', flat=True)
        
        # Get available technicians with required skills and location
        available_technicians = User.objects.filter(
            id__in=skilled_technicians,
            role='technician',
            is_available=True,
            status='active'
        ).exclude(
            assigned_tickets__status__in=['Not Started', 'In Progress']
        )
        
        if not available_technicians:
            return Response(
                {'error': 'No available technicians with required skills', 'success': False},
                status=status.HTTP_404_NOT_FOUND
            )
        
        ranked_candidates = []
        for tech in available_technicians:
            candidate = score_technician_fit(ticket, tech, request_lat, request_lon)
            if candidate is not None:
                candidate['technician'] = tech
                ranked_candidates.append(candidate)

        if not ranked_candidates:
            return Response(
                {'error': 'No technicians have enough routing and skill data for smart assignment', 'success': False},
                status=status.HTTP_404_NOT_FOUND
            )

        ranked_candidates.sort(key=lambda item: item['score'], reverse=True)
        best_candidate = ranked_candidates[0]
        selected_technician = best_candidate['technician']

        if selected_technician:
            ticket.technician = selected_technician
            ticket.auto_assigned = True
            ticket.assigned_at = timezone.now()
            ticket.smart_assignment_score = best_candidate['score']
            ticket.smart_assignment_summary = best_candidate['summary']
            ticket.save()
            sync_technician_availability(selected_technician)
            inventory_summary = sync_ticket_reservations(ticket, performed_by=request.user)

            # compute route details
            try:
                loc = ticket.request.location
                if loc.latitude and loc.longitude and selected_technician.current_latitude and selected_technician.current_longitude:
                    from .ors_utils import get_route
                    route = get_route(
                        (float(loc.longitude), float(loc.latitude)),
                        (float(selected_technician.current_longitude), float(selected_technician.current_latitude))
                    )
                    if route and 'features' in route and route['features']:
                        geom = route['features'][0].get('geometry')
                        props = route['features'][0].get('properties', {}).get('segments', [{}])[0]
                        ticket.route_geometry = geom
                        ticket.route_distance = props.get('distance')
                        ticket.route_duration = props.get('duration')
                        ticket.save()
            except Exception as e:
                logger.warning(f"Route calculation failed for ticket {ticket.id}: {e}")
            
            # Create status history
            ServiceStatusHistory.objects.create(
                ticket=ticket,
                status=ticket.status,
                changed_by=request.user,
                notes=(
                    f"Smart-assigned to {selected_technician.username} "
                    f"(score {best_candidate['score']}, distance {best_candidate['distance_km']:.2f} km, "
                    f"{best_candidate['summary']})"
                )
            )
            
            # Notify technician
            create_notification(
                selected_technician,
                f"You have been auto-assigned to ticket #{ticket.id}",
                'info'
            )
            send_notification_email(
                selected_technician,
                'New Auto-Assigned Ticket',
                f'You have been auto-assigned to ticket #{ticket.id} for {service_type.name}'
            )
            create_notification(
                ticket.request.client,
                f"Your service ticket #{ticket.id} was auto-assigned to {selected_technician.username}.",
                'info'
            )
            
            return Response({
                'success': True,
                'message': 'Technician auto-assigned',
                'ticket_id': ticket.id,
                'technician': {
                    'id': selected_technician.id,
                    'username': selected_technician.username
                },
                'distance_km': best_candidate['distance_km'],
                'assignment_score': best_candidate['score'],
                'assignment_summary': best_candidate['summary'],
                'candidate_ranking': [
                    {
                        'technician_id': item['technician'].id,
                        'technician_name': item['technician'].username,
                        'score': item['score'],
                        'distance_km': item['distance_km'],
                        'skill_level': item['skill_level'],
                    }
                    for item in ranked_candidates[:3]
                ],
                'route_distance': ticket.route_distance,
                'route_duration': ticket.route_duration,
                'inventory_summary': inventory_summary,
            })
        
        return Response(
            {'error': 'Could not find suitable technician', 'success': False},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update ticket status with history tracking"""
        ticket = self.get_object()
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if not new_status:
            return Response({'error': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            resolved_status = apply_ticket_status_change(
                ticket,
                new_status,
                changed_by=request.user,
                notes=notes or f'Status updated to {new_status}',
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        create_notification(
            ticket.request.client,
            f"Service status updated to {resolved_status} for ticket #{ticket.id}",
            'info'
        )
        if ticket.technician and ticket.technician != request.user:
            create_notification(
                ticket.technician,
                f"Ticket #{ticket.id} status was updated to {resolved_status}.",
                'info'
            )
        
        return Response({
            'success': True,
            'message': 'Status updated',
            'ticket_id': ticket.id,
            'status': resolved_status
        })
    
    @action(detail=True, methods=['post'])
    def start_work(self, request, pk=None):
        """Mark ticket as started"""
        ticket = self.get_object()
        if ticket.technician_id != request.user.id:
            raise PermissionDenied('You can only start your own assigned tickets.')

        try:
            resolved_status = apply_ticket_status_change(
                ticket,
                'In Progress',
                changed_by=request.user,
                notes='Work started',
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        create_notification(
            ticket.request.client,
            f"Work has started for ticket #{ticket.id}.",
            'info'
        )
        
        return Response({'status': resolved_status, 'start_time': ticket.start_time})
    
    @action(detail=True, methods=['post'])
    def complete_work(self, request, pk=None):
        """Mark ticket as completed"""
        ticket = self.get_object()
        if ticket.technician_id != request.user.id:
            raise PermissionDenied('You can only complete your own assigned tickets.')

        try:
            resolved_status = apply_ticket_status_change(
                ticket,
                'Completed',
                changed_by=request.user,
                notes='Work completed',
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Notify client
        create_notification(
            ticket.request.client,
            f"Your service ticket #{ticket.id} has been completed!",
            'success'
        )
        
        return Response({'status': resolved_status, 'end_time': ticket.end_time})

    @action(detail=True, methods=['post'])
    def request_reschedule(self, request, pk=None):
        ticket = self.get_object()
        if request.user.role != 'client' or ticket.request.client_id != request.user.id:
            raise PermissionDenied('You can only request reschedules for your own tickets.')
        if ticket.status not in CLIENT_RESCHEDULABLE_TICKET_STATUSES:
            return Response(
                {'error': 'Reschedules can only be requested before work has started.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        preferred_date_value = request.data.get('preferred_date')
        preferred_time_slot = normalize_time_slot(request.data.get('preferred_time_slot'))
        reason = str(request.data.get('reason', '')).strip()

        if not preferred_date_value or not preferred_time_slot or not reason:
            return Response(
                {'error': 'preferred_date, preferred_time_slot, and reason are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        preferred_date = parse_date(str(preferred_date_value))
        if preferred_date is None:
            return Response({'error': 'preferred_date must be a valid date'}, status=status.HTTP_400_BAD_REQUEST)
        if preferred_date < timezone.localdate():
            return Response({'error': 'preferred_date cannot be in the past'}, status=status.HTTP_400_BAD_REQUEST)

        request_obj = ticket.request
        request_obj.preferred_date = preferred_date
        request_obj.preferred_time_slot = preferred_time_slot
        request_obj.scheduling_notes = reason
        request_obj.save(update_fields=['preferred_date', 'preferred_time_slot', 'scheduling_notes', 'updated_at'])

        ticket.reschedule_requested = True
        ticket.reschedule_reason = reason
        ticket.reschedule_requested_at = timezone.now()
        ticket.save(update_fields=['reschedule_requested', 'reschedule_reason', 'reschedule_requested_at', 'updated_at'])

        ServiceStatusHistory.objects.create(
            ticket=ticket,
            status=ticket.status,
            changed_by=request.user,
            notes=(
                f"Client requested reschedule to {preferred_date.isoformat()} "
                f"({preferred_time_slot}): {reason}"
            )
        )

        recipients = User.objects.filter(role__in=['admin', 'supervisor'])
        if ticket.supervisor_id:
            recipients = recipients | User.objects.filter(id=ticket.supervisor_id)

        for recipient in recipients.distinct():
            create_notification(
                recipient,
                f"Ticket #{ticket.id} has a new reschedule request for {preferred_date.isoformat()} ({preferred_time_slot}).",
                'warning'
            )

        return Response({
            'status': 'Reschedule requested',
            'preferred_date': preferred_date,
            'preferred_time_slot': preferred_time_slot,
            'reason': reason,
        })

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status not in CLIENT_RESCHEDULABLE_TICKET_STATUSES:
            return Response(
                {'error': 'Only tickets that have not started can be rescheduled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        scheduled_date_value = request.data.get('scheduled_date') or ticket.request.preferred_date
        scheduled_time_slot = normalize_time_slot(
            request.data.get('scheduled_time_slot') or ticket.request.preferred_time_slot
        )
        scheduled_time = None
        if request.data.get('scheduled_time'):
            scheduled_time = parse_time(str(request.data.get('scheduled_time')))
            if scheduled_time is None:
                return Response({'error': 'scheduled_time must be a valid time'}, status=status.HTTP_400_BAD_REQUEST)

        if scheduled_date_value in [None, '']:
            return Response({'error': 'scheduled_date is required'}, status=status.HTTP_400_BAD_REQUEST)

        scheduled_date = scheduled_date_value
        if not hasattr(scheduled_date, 'isoformat'):
            scheduled_date = parse_date(str(scheduled_date_value))
        if scheduled_date is None:
            return Response({'error': 'scheduled_date must be a valid date'}, status=status.HTTP_400_BAD_REQUEST)
        if scheduled_date < timezone.localdate():
            return Response({'error': 'scheduled_date cannot be in the past'}, status=status.HTTP_400_BAD_REQUEST)

        apply_schedule_fields(
            ticket,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            scheduled_time_slot=scheduled_time_slot,
        )
        ticket.reschedule_requested = False
        ticket.reschedule_reason = None
        ticket.reschedule_requested_at = None
        ticket.save()

        request_obj = ticket.request
        request_obj.preferred_date = scheduled_date
        request_obj.preferred_time_slot = scheduled_time_slot
        if request.data.get('notes'):
            request_obj.scheduling_notes = str(request.data.get('notes')).strip()
        request_obj.save(update_fields=['preferred_date', 'preferred_time_slot', 'scheduling_notes', 'updated_at'])

        ServiceStatusHistory.objects.create(
            ticket=ticket,
            status=ticket.status,
            changed_by=request.user,
            notes=(
                f"Schedule confirmed for {scheduled_date.isoformat()} "
                f"({scheduled_time_slot or 'time to be confirmed'})"
            )
        )

        create_notification(
            ticket.request.client,
            f"Ticket #{ticket.id} was rescheduled to {scheduled_date.isoformat()} ({scheduled_time_slot or 'time TBD'}).",
            'info'
        )
        if ticket.technician:
            create_notification(
                ticket.technician,
                f"Ticket #{ticket.id} was rescheduled to {scheduled_date.isoformat()} ({scheduled_time_slot or 'time TBD'}).",
                'info'
            )

        return Response({
            'status': 'Schedule updated',
            'scheduled_date': ticket.scheduled_date,
            'scheduled_time': ticket.scheduled_time,
            'scheduled_time_slot': ticket.scheduled_time_slot,
        })

    @action(detail=True, methods=['post'])
    def add_notes(self, request, pk=None):
        ticket = self.get_object()
        notes = request.data.get('notes', '').strip()
        if not notes:
            return Response({'error': 'Notes are required'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.notes = f"{ticket.notes or ''}\n{notes}".strip()
        ticket.save()

        ServiceStatusHistory.objects.create(
            ticket=ticket,
            status=ticket.status,
            changed_by=request.user,
            notes=f"Technician notes: {notes}"
        )

        return Response({'status': 'Notes added', 'notes': ticket.notes})

    @action(detail=True, methods=['post'])
    def submit_feedback(self, request, pk=None):
        ticket = self.get_object()
        if request.user.role != 'client' or ticket.request.client_id != request.user.id:
            raise PermissionDenied('You can only rate your own completed tickets.')
        if ticket.status != 'Completed':
            return Response({'error': 'Feedback can only be submitted for completed tickets'}, status=status.HTTP_400_BAD_REQUEST)

        rating = request.data.get('rating', request.data.get('client_rating'))
        feedback = str(request.data.get('feedback', request.data.get('client_feedback', ''))).strip()

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return Response({'error': 'rating must be a number from 1 to 5'}, status=status.HTTP_400_BAD_REQUEST)

        if rating < 1 or rating > 5:
            return Response({'error': 'rating must be between 1 and 5'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.client_rating = rating
        ticket.client_feedback = feedback or None
        ticket.save(update_fields=['client_rating', 'client_feedback', 'updated_at'])

        if ticket.technician:
            create_notification(
                ticket.technician,
                f"Client feedback received for ticket #{ticket.id}: {rating}/5",
                'info'
            )

        return Response({
            'status': 'Feedback submitted',
            'client_rating': ticket.client_rating,
            'client_feedback': ticket.client_feedback,
        })

    @action(detail=True, methods=['post'])
    def upload_photos(self, request, pk=None):
        ticket = self.get_object()
        photos = request.data.get('photos', []) or []
        videos = request.data.get('videos', []) or []
        media = request.data.get('media', []) or []
        proof_media = normalize_proof_media_payload(photos=photos, videos=videos, media=media)
        if not proof_media:
            return Response({'error': 'At least one photo or video proof entry is required'}, status=status.HTTP_400_BAD_REQUEST)

        checklist, _ = InspectionChecklist.objects.get_or_create(ticket=ticket)
        checklist.proof_media = list(checklist.proof_media or []) + proof_media
        checklist.save(update_fields=['proof_media'])

        photo_count = sum(1 for item in proof_media if item['type'] == 'photo')
        video_count = sum(1 for item in proof_media if item['type'] == 'video')
        ServiceStatusHistory.objects.create(
            ticket=ticket,
            status=ticket.status,
            changed_by=request.user,
            notes=f"Proof uploaded: {photo_count} photo(s), {video_count} video(s)"
        )

        return Response({
            'status': 'Proof uploaded',
            'photos': [item for item in proof_media if item['type'] == 'photo'],
            'videos': [item for item in proof_media if item['type'] == 'video'],
            'media': proof_media,
        })

    @action(detail=True, methods=['post'])
    def request_parts(self, request, pk=None):
        ticket = self.get_object()
        requested_parts = request.data.get('parts', '')
        if not requested_parts:
            return Response({'error': 'Requested parts must be provided'}, status=status.HTTP_400_BAD_REQUEST)
        if ticket.status not in PARTS_REQUEST_TICKET_STATUSES:
            return Response(
                {'error': 'Parts can only be requested after work has started.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            apply_ticket_status_change(
                ticket,
                'On Hold',
                changed_by=request.user,
                notes=f"Parts requested: {requested_parts}",
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Notify supervisor and admin that parts are requested
        supervisors = User.objects.filter(role='supervisor')
        admins = User.objects.filter(role='admin')
        for u in list(supervisors) + list(admins):
            create_notification(
                u,
                f"Parts requested for ticket #{ticket.id}: {requested_parts}",
                'warning'
            )
        create_notification(
            ticket.request.client,
            f"Ticket #{ticket.id} is temporarily on hold while parts are being arranged.",
            'info'
        )

        return Response({'status': 'Parts requested', 'parts': requested_parts})

    @action(detail=True, methods=['post'])
    def contact_client(self, request, pk=None):
        ticket = self.get_object()
        if ticket.status not in CONTACTABLE_TICKET_STATUSES:
            return Response(
                {'error': 'Clients can only be contacted while the ticket is active.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        method = request.data.get('method', 'phone')
        message = request.data.get('message', 'Technician needs to contact you regarding the service ticket.')

        # Notify client in-app and via email where available
        client = ticket.request.client
        create_notification(client, f"{request.user.username} ({method}) says: {message}", 'info')
        if client.email:
            send_notification_email(client, 'Technician Contact', message)

        ServiceStatusHistory.objects.create(
            ticket=ticket,
            status=ticket.status,
            changed_by=request.user,
            notes=f"Contact client via {method}: {message}"
        )

        return Response({'status': 'Client contacted', 'method': method})

    @action(detail=True, methods=['get'])
    def inventory_summary(self, request, pk=None):
        ticket = self.get_object()
        return Response({
            'ticket_id': ticket.id,
            'inventory_reservations': serialize_ticket_inventory(ticket),
        })


class TechnicianClientsView(viewsets.ViewSet):
    """View for technicians to see their assigned clients with location data"""
    permission_classes = [IsTechnician]

    def list(self, request):
        """Return list of clients assigned to the current technician"""
        technician = request.user

        # Get all tickets assigned to this technician
        tickets = ServiceTicket.objects.filter(
            technician=technician
        ).select_related('request__client', 'request__location')

        # Extract unique clients with their location data
        clients_data = []
        seen_clients = set()

        for ticket in tickets:
            client = ticket.request.client
            if client.id not in seen_clients:
                seen_clients.add(client.id)

                # Get location data (ServiceLocation may not exist for every request)
                try:
                    location = ticket.request.location
                except ServiceLocation.DoesNotExist:
                    location = None

                client_data = {
                    'id': client.id,
                    'name': f"{client.first_name} {client.last_name}".strip() or client.username,
                    'username': client.username,
                    'email': client.email,
                    'phone': getattr(client, 'phone', ''),
                    'address': location.address if location else getattr(client, 'address', ''),
                    'latitude': float(location.latitude) if location and location.latitude else None,
                    'longitude': float(location.longitude) if location and location.longitude else None,
                    'status': ticket.status.lower().replace(' ', '_'),
                    'ticket_id': ticket.id,
                    'scheduled_date': ticket.scheduled_date,
                    'service_type': ticket.request.service_type.name
                }
                clients_data.append(client_data)

        return Response(clients_data)


class TechnicianDashboardView(viewsets.ViewSet):
    """Technician dashboard with real data from database"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get technician dashboard data - consistent field naming"""
        technician = request.user
        if technician.role != 'technician':
            return Response({'error': 'Only technicians can access this dashboard'}, status=403)

        # Get technician's assigned tickets
        assigned_tickets = ServiceTicket.objects.filter(
            technician=technician
        ).select_related('request__service_type', 'request__client', 'request__location')

        # Today's schedule
        today = timezone.now().date()
        todays_tickets = assigned_tickets.filter(scheduled_date=today)

        # Active tickets (not completed)
        active_tickets = assigned_tickets.filter(
            status__in=['Not Started', 'In Progress', 'On Hold']
        )

        # Recent activity (last 7 days)
        week_ago = timezone.now().date() - timezone.timedelta(days=7)
        recent_tickets = assigned_tickets.filter(
            Q(request__request_date__gte=week_ago) | Q(assigned_at__gte=week_ago)
        ).order_by('-assigned_at')[:10]

        # Calculate stats
        total_assigned = assigned_tickets.count()
        completed_today = assigned_tickets.filter(
            status='Completed',
            assigned_at__date=today
        ).count()
        pending_count = active_tickets.count()

        # Current location (if available)
        current_location = None
        if technician.current_latitude and technician.current_longitude:
            current_location = {
                'latitude': technician.current_latitude,
                'longitude': technician.current_longitude,
                'last_update': technician.last_location_update
            }

        return Response({
            'technician': {
                'id': technician.id,
                'username': technician.username,
                'is_available': technician.is_available,
                'current_location': current_location
            },
            'stats': {
                'total_assigned': total_assigned,
                'completed_today': completed_today,
                'pending_jobs': pending_count,
                'active_jobs': active_tickets.count()
            },
            'todays_schedule': [{
                'id': ticket.id,
                'ticket_id': f'TKT-{ticket.id}',
                'service_type': ticket.request.service_type.name,
                'client': ticket.request.client.username,
                'location': _get_request_address(ticket.request),
                'scheduled_time': str(ticket.scheduled_time) if ticket.scheduled_time else None,
                'scheduled_time_slot': ticket.scheduled_time_slot,
                'status': ticket.status,
                'priority': ticket.request.priority,
                'notes': ticket.notes,
                'assigned_at': ticket.assigned_at
            } for ticket in todays_tickets],
            'active_jobs': [{
                'id': ticket.id,
                'ticket_id': f'TKT-{ticket.id}',
                'service_type': ticket.request.service_type.name,
                'client': ticket.request.client.username,
                'location': _get_request_address(ticket.request),
                'status': ticket.status,
                'scheduled_date': ticket.scheduled_date,
                'scheduled_time_slot': ticket.scheduled_time_slot,
                'priority': ticket.request.priority
            } for ticket in active_tickets],
            'recent_activity': [{
                'id': ticket.id,
                'ticket_id': f'TKT-{ticket.id}',
                'service_type': ticket.request.service_type.name,
                'client': ticket.request.client.username,
                'status': ticket.status,
                'assigned_at': ticket.assigned_at,
                'created_at': ticket.request.request_date
            } for ticket in recent_tickets]
        })


class TechnicianJobsView(viewsets.ViewSet):
    """View for technician jobs and schedule - uses consistent field naming with ServiceTicketViewSet"""
    permission_classes = [IsTechnician]

    def list(self, request):
        """Get technician's assigned jobs"""
        technician = request.user

        tickets = ServiceTicket.objects.filter(
            technician=technician
        ).select_related(
            'request__service_type', 'request__client', 'request__location'
        ).order_by('-scheduled_date')

        jobs = []
        for ticket in tickets:
            try:
                location = ticket.request.location
                location_address = location.address if location else None
            except ServiceLocation.DoesNotExist:
                location_address = None

            jobs.append({
                'id': ticket.id,
                'ticket_id': f'TKT-{ticket.id}',
                'service_type': ticket.request.service_type.name,
                'client': ticket.request.client.username,
                'address': location_address or '',
                'status': ticket.status,  # Keep original status, don't lowercase
                'priority': ticket.request.priority,
                'scheduled_date': ticket.scheduled_date,
                'scheduled_time': str(ticket.scheduled_time) if ticket.scheduled_time else None,
                'scheduled_time_slot': ticket.scheduled_time_slot,
                'notes': ticket.notes or '',
                'technician': ticket.technician.username if ticket.technician else None,
                'created_at': ticket.request.request_date
            })

        return Response(jobs)

    def update_status(self, request, pk=None):
        """Update a technician job status using the ticket workflow"""
        try:
            ticket = ServiceTicket.objects.get(pk=pk, technician=request.user)
        except ServiceTicket.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

        requested_status = str(request.data.get('status', '')).strip().lower()
        status_map = {
            'accepted': 'Not Started',
            'in_progress': 'In Progress',
            'completed': 'Completed'
        }
        new_status = status_map.get(requested_status)
        if not new_status:
            return Response({'error': 'Unsupported status'}, status=status.HTTP_400_BAD_REQUEST)
        if requested_status == 'accepted' and ticket.status == 'Not Started':
            ServiceStatusHistory.objects.create(
                ticket=ticket,
                status='Not Started',
                changed_by=request.user,
                notes='Technician acknowledged assignment'
            )
            return Response({'status': 'Not Started', 'ticket_id': ticket.id})

        try:
            resolved_status = apply_ticket_status_change(
                ticket,
                new_status,
                changed_by=request.user,
                notes=f'Technician updated job status to {new_status}'
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if resolved_status == 'Completed':
            create_notification(
                ticket.request.client,
                f"Your service ticket #{ticket.id} has been completed!",
                'success'
            )
        elif resolved_status == 'In Progress':
            create_notification(
                ticket.request.client,
                f"Work has started for ticket #{ticket.id}.",
                'info'
            )

        return Response({'status': resolved_status, 'ticket_id': ticket.id})


class TechnicianScheduleView(viewsets.ViewSet):
    """View for technician schedule - uses consistent field naming"""
    permission_classes = [IsTechnician]

    def list(self, request):
        """Get technician's schedule"""
        technician = request.user

        # Get today's and upcoming tickets
        today = timezone.now().date()
        tickets = ServiceTicket.objects.filter(
            technician=technician,
            scheduled_date__gte=today
        ).select_related(
            'request__service_type', 'request__client', 'request__location'
        ).order_by('scheduled_date')

        schedule = []
        for ticket in tickets:
            try:
                location = ticket.request.location
                location_address = location.address if location else None
            except ServiceLocation.DoesNotExist:
                location_address = None

            schedule.append({
                'id': ticket.id,
                'ticket_id': f'TKT-{ticket.id}',
                'service_type': ticket.request.service_type.name,
                'client': ticket.request.client.username,
                'location': location_address,
                'status': ticket.status,  # Keep original status
                'priority': ticket.request.priority,
                'scheduled_date': ticket.scheduled_date,
                'scheduled_time': str(ticket.scheduled_time) if ticket.scheduled_time else None,
                'scheduled_time_slot': ticket.scheduled_time_slot,
                'notes': ticket.notes or ''
            })

        return Response(schedule)


class TechnicianProfileView(viewsets.ViewSet):
    permission_classes = [IsTechnician]

    def list(self, request):
        technician = request.user
        completed_tickets = ServiceTicket.objects.filter(technician=technician, status='Completed')
        avg_rating = completed_tickets.exclude(client_rating__isnull=True).aggregate(avg=Avg('client_rating')).get('avg')
        skills = TechnicianSkill.objects.filter(technician=technician).select_related('service_type')

        return Response({
            'phone': technician.phone or '',
            'email': technician.email or '',
            'skills': ', '.join(skill.service_type.name for skill in skills),
            'totalCompleted': completed_tickets.count(),
            'avgCompletionTime': '',
            'rating': float(avg_rating) if avg_rating is not None else 0,
            'status': 'Available' if technician.is_available and technician.status == 'active' else technician.status.title()
        })

    def update(self, request, pk=None):
        serializer = SelfUserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return self.list(request)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TechnicianHistoryView(viewsets.ViewSet):
    permission_classes = [IsTechnician]

    def list(self, request):
        tickets = ServiceTicket.objects.filter(
            technician=request.user,
            status='Completed'
        ).select_related('request__service_type', 'request__client').order_by('-completed_date', '-updated_at')

        history = [{
            'id': ticket.id,
            'service': ticket.request.service_type.name if ticket.request.service_type else 'Service',
            'client': ticket.request.client.username if ticket.request.client else 'Unknown',
            'ticketId': ticket.id,
            'scheduledDate': ticket.completed_date or ticket.scheduled_date,
            'priority': ticket.request.priority if ticket.request else '',
            'notes': ticket.notes or ''
        } for ticket in tickets]
        return Response(history)


class TechnicianSkillViewSet(viewsets.ModelViewSet):
    queryset = TechnicianSkill.objects.select_related('technician', 'service_type')
    serializer_class = TechnicianSkillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrSupervisor()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'supervisor']:
            return self.queryset
        if user.role == 'technician':
            return self.queryset.filter(technician=user)
        return self.queryset.none()


class ServiceStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceStatusHistory.objects.select_related(
        'ticket__request__client',
        'ticket__request__service_type',
        'changed_by',
    )
    serializer_class = ServiceStatusHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        visible_tickets = get_visible_service_tickets_queryset(self.request.user)
        return self.queryset.filter(ticket__in=visible_tickets)


class InspectionChecklistViewSet(viewsets.ModelViewSet):
    queryset = InspectionChecklist.objects.select_related(
        'ticket__request__client',
        'ticket__request__service_type',
        'ticket__technician',
        'completed_by',
    )
    serializer_class = InspectionChecklistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'complete']:
            return [IsAdminOrSupervisorOrTechnician()]
        if self.action == 'destroy':
            return [IsAdminOrSupervisor()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        visible_tickets = get_visible_service_tickets_queryset(self.request.user)
        return self.queryset.filter(ticket__in=visible_tickets)

    def perform_create(self, serializer):
        ticket = serializer.validated_data['ticket']
        if self.request.user.role == 'technician' and ticket.technician_id != self.request.user.id:
            raise PermissionDenied('You can only create inspection checklists for your assigned tickets.')
        checklist = serializer.save()
        sync_ticket_maintenance_schedule(checklist.ticket)
        # Create notification for technician
        if checklist.ticket.technician:
            create_notification(
                checklist.ticket.technician,
                f"New inspection checklist created for ticket #{checklist.ticket.id}",
                'info'
            )

    def perform_update(self, serializer):
        checklist = serializer.save()
        sync_ticket_maintenance_schedule(checklist.ticket)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark inspection as completed"""
        checklist = self.get_object()
        checklist.is_completed = True
        checklist.completed_at = timezone.now()
        checklist.completed_by = request.user
        checklist.save()
        sync_ticket_maintenance_schedule(checklist.ticket)
        
        create_notification(
            checklist.ticket.request.client,
            f"Inspection completed for ticket #{checklist.ticket.id}",
            'info'
        )
        
        return Response({'status': 'Inspection completed'})


class TechnicianLocationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TechnicianLocationHistory.objects.select_related('technician')
    serializer_class = TechnicianLocationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'update_location':
            return [IsTechnician()]
        if self.action in ['nearby_technicians', 'all_technicians_locations']:
            return [IsAdminOrSupervisor()]
        return [IsAdminOrSupervisorOrTechnician()]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'supervisor']:
            return self.queryset
        if user.role == 'technician':
            return self.queryset.filter(technician=user)
        return self.queryset.none()

    @action(detail=False, methods=['post'])
    def update_location(self, request):
        """Update technician's current location"""
        technician = request.user
        
        if technician.role != 'technician':
            return Response({'error': 'Only technicians can update location'}, status=status.HTTP_403_FORBIDDEN)
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        accuracy = request.data.get('accuracy', 0)
        
        if not latitude or not longitude:
            return Response({'error': 'Latitude and longitude required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update technician's current location
        technician.current_latitude = latitude
        technician.current_longitude = longitude
        technician.last_location_update = timezone.now()
        technician.save()
        
        # Save to history
        TechnicianLocationHistory.objects.create(
            technician=technician,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy
        )
        
        return Response({'status': 'Location updated'})
    
    @action(detail=False, methods=['get'])
    def nearby_technicians(self, request):
        """Get all technicians near a location"""
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius_km = float(request.query_params.get('radius', 10))
        
        if not latitude or not longitude:
            return Response({'error': 'Latitude and longitude required'}, status=status.HTTP_400_BAD_REQUEST)
        
        technicians = User.objects.filter(
            role='technician',
            is_available=True,
            status='active'
        )
        
        nearby = []
        for tech in technicians:
            if tech.current_latitude and tech.current_longitude:
                distance = calculate_distance(
                    float(latitude), float(longitude),
                    tech.current_latitude, tech.current_longitude
                )
                if distance <= radius_km:
                    nearby.append({
                        'id': tech.id,
                        'username': tech.username,
                        'latitude': tech.current_latitude,
                        'longitude': tech.current_longitude,
                        'distance_km': round(distance, 2)
                    })
        
        return Response(nearby)
    
    @action(detail=False, methods=['get'])
    def all_technicians_locations(self, request):
        """Get all technicians current locations (for admin map)"""
        technicians = User.objects.filter(
            role='technician',
            status='active'
        ).values('id', 'username', 'current_latitude', 'current_longitude', 'is_available')
        
        return Response(technicians)


# GIS Dashboard View
class GISDashboardView(viewsets.ViewSet):
    """Geographic Information System (GIS) Dashboard - Mapping component for visualizing geographic service data."""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard_data(self, request):
        """Get all data for GIS dashboard"""
        # Get all technicians with locations
        technicians = User.objects.filter(
            role='technician',
            status='active'
        ).values('id', 'username', 'current_latitude', 'current_longitude', 'is_available')
        
        # Get all pending service requests with locations
        pending_requests = ServiceRequest.objects.filter(
            status__in=['Pending', 'Approved']
        ).select_related('client', 'service_type')
        
        requests_data = []
        for req in pending_requests:
            try:
                location = req.location
                requests_data.append({
                    'id': req.id,
                    'service_type': req.service_type.name,
                    'client': req.client.username,
                    'priority': req.priority,
                    'status': req.status,
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'address': location.address
                })
            except ServiceLocation.DoesNotExist:
                pass
        
        # Get all active tickets
        active_tickets = ServiceTicket.objects.filter(
            status__in=['Not Started', 'In Progress']
        ).select_related('technician', 'request__service_type')
        
        tickets_data = []
        for ticket in active_tickets:
            try:
                location = ticket.request.location
                tickets_data.append({
                    'id': ticket.id,
                    'service_type': ticket.request.service_type.name,
                    'technician': ticket.technician.username if ticket.technician else None,
                    'status': ticket.status,
                    'latitude': location.latitude,
                    'longitude': location.longitude
                })
            except ServiceLocation.DoesNotExist:
                pass
        
        return Response({
            'technicians': list(technicians),
            'service_requests': requests_data,
            'active_tickets': tickets_data
        })
    
    @action(detail=False, methods=['get'])
    def heatmap_data(self, request):
        """Get data for Coverage Heatmap - GIS-based visualization of service request concentrations."""
        # Get completed requests grouped by location
        completed = ServiceRequest.objects.filter(
            status='Completed'
        ).select_related('service_type', 'location')
        
        heatmap_points = []
        for req in completed:
            try:
                if req.location and req.location.latitude:
                    heatmap_points.append({
                        'lat': float(req.location.latitude),
                        'lng': float(req.location.longitude),
                        'service_type': req.service_type.name,
                        'count': 1
                    })
            except ServiceLocation.DoesNotExist:
                pass
        
        return Response(heatmap_points)


# Analytics ViewSets
class ServiceAnalyticsViewSet(viewsets.ModelViewSet):
    """Descriptive Analytics - Summarization and analysis of historical service data for operational performance evaluation."""
    queryset = ServiceAnalytics.objects.all()
    serializer_class = ServiceAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard_metrics(self, request):
        """Get current dashboard metrics"""
        today = timezone.now().date()
        
        # Get today's analytics or create if doesn't exist
        analytics = ServiceAnalytics.objects.filter(date=today).first()
        if not analytics:
            analytics = self._generate_daily_analytics(today)
        
        serializer = self.get_serializer(analytics)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get service trends over time"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)
        
        trends = ServiceAnalytics.objects.filter(
            date__gte=start_date
        ).order_by('date')
        
        serializer = self.get_serializer(trends, many=True)
        return Response(serializer.data)
    
    def _generate_daily_analytics(self, date):
        """Generate analytics for a specific date"""
        # Calculate metrics from actual data
        total_requests = ServiceRequest.objects.filter(
            request_date__date=date
        ).count()
        
        completed_requests = ServiceRequest.objects.filter(
            status='Completed',
            updated_at__date=date
        ).count()
        
        pending_requests = ServiceRequest.objects.filter(
            status__in=['Pending', 'Approved'],
            request_date__date=date
        ).count()
        
        cancelled_requests = ServiceRequest.objects.filter(
            status='Cancelled',
            updated_at__date=date
        ).count()
        
        # Create analytics record
        analytics = ServiceAnalytics.objects.create(
            date=date,
            total_requests=total_requests,
            completed_requests=completed_requests,
            pending_requests=pending_requests,
            cancelled_requests=cancelled_requests,
            avg_response_time_hours=2.5,  # Placeholder - would calculate from actual data
            avg_completion_time_hours=4.2,  # Placeholder
            technician_utilization_rate=0.75,  # Placeholder
            service_area_coverage=150.5,  # Placeholder
            popular_locations=[],  # Would populate from location data
            satisfaction_score=4.2  # Placeholder
        )
        
        return analytics


class TechnicianPerformanceViewSet(viewsets.ModelViewSet):
    queryset = TechnicianPerformance.objects.all()
    serializer_class = TechnicianPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'technician':
            return TechnicianPerformance.objects.filter(technician=user)
        return TechnicianPerformance.objects.all()
    
    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Get technician performance leaderboard"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)
        
        # Aggregate performance over the period
        performances = TechnicianPerformance.objects.filter(
            date__gte=start_date
        ).values('technician__username').annotate(
            total_completed=Sum('tickets_completed'),
            avg_satisfaction=Avg('customer_satisfaction'),
            total_hours=Sum('total_work_hours')
        ).order_by('-total_completed')
        
        return Response(list(performances))


class DemandForecastViewSet(viewsets.ModelViewSet):
    """Demand Forecasting - Estimation of future service demand using AI and historical data analysis."""
    queryset = DemandForecast.objects.all()
    serializer_class = DemandForecastSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def generate_forecast(self, request):
        """Generate demand forecast for upcoming periods"""
        service_type_id = request.data.get('service_type_id')
        periods = int(request.data.get('periods', 7))  # Default 7 days
        
        if not service_type_id:
            return Response({'error': 'service_type_id required'}, status=400)
        
        try:
            service_type = ServiceType.objects.get(id=service_type_id)
        except ServiceType.DoesNotExist:
            return Response({'error': 'Service type not found'}, status=404)
        
        forecasts = []
        base_date = timezone.now().date()
        
        # Simple forecasting algorithm (would be more sophisticated in production)
        for i in range(periods):
            forecast_date = base_date + timezone.timedelta(days=i)
            
            # Get historical data for this service type
            historical_requests = ServiceRequest.objects.filter(
                service_type=service_type,
                request_date__date__lte=forecast_date - timezone.timedelta(days=1),
                request_date__date__gte=forecast_date - timezone.timedelta(days=30)
            ).count()
            
            # Calculate average daily demand
            historical_average = historical_requests / 30 if historical_requests > 0 else 1
            
            # Apply seasonal adjustments (simplified)
            day_of_week = forecast_date.weekday()
            seasonal_multiplier = 1.0
            if day_of_week >= 5:  # Weekend
                seasonal_multiplier = 0.8
            elif day_of_week == 0:  # Monday
                seasonal_multiplier = 1.2
            
            predicted_requests = int(historical_average * seasonal_multiplier)
            
            forecast = DemandForecast.objects.create(
                service_type=service_type,
                forecast_date=forecast_date,
                forecast_period='daily',
                predicted_requests=max(1, predicted_requests),  # At least 1 request
                confidence_level=0.75,
                weather_impact=0.0,  # Would integrate weather API
                seasonal_trend=seasonal_multiplier,
                historical_average=int(historical_average)
            )
            
            forecasts.append(forecast)
        
        serializer = self.get_serializer(forecasts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def accuracy_report(self, request):
        """Get forecast accuracy report"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)
        
        forecasts = DemandForecast.objects.filter(
            forecast_date__lt=timezone.now().date(),
            forecast_date__gte=start_date
        ).exclude(actual_requests__isnull=True)
        
        accuracy_data = []
        for forecast in forecasts:
            if forecast.actual_requests is not None and forecast.predicted_requests > 0:
                accuracy = 1 - abs(forecast.actual_requests - forecast.predicted_requests) / forecast.predicted_requests
                forecast.forecast_accuracy = max(0, accuracy)  # Ensure non-negative
                forecast.save()
                
                accuracy_data.append({
                    'service_type': forecast.service_type.name,
                    'forecast_date': forecast.forecast_date,
                    'predicted': forecast.predicted_requests,
                    'actual': forecast.actual_requests,
                    'accuracy': round(forecast.forecast_accuracy * 100, 1)
                })
        
        return Response(accuracy_data)


class ServiceTrendViewSet(viewsets.ModelViewSet):
    queryset = ServiceTrend.objects.all()
    serializer_class = ServiceTrendSerializer
    permission_classes = [permissions.IsAuthenticated]


class StatusReportsViewSet(viewsets.ViewSet):
    """Status reports for various operational aspects"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def scheduling_dispatch_report(self, request):
        """Report on scheduling and dispatching efficiency with completion progress"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)

        # Ticket scheduling metrics
        total_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date)
        ).count()

        # Calculate completion stages
        scheduled_count = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            scheduled_date__isnull=False
        ).count()

        assigned_count = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            technician__isnull=False
        ).count()

        in_progress_count = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            status='In Progress'
        ).count()

        completed_count = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            status='Completed'
        ).count()

        # Calculate percentages for each stage
        scheduled_pct = round((scheduled_count / total_tickets * 100) if total_tickets > 0 else 0, 1)
        assigned_pct = round((assigned_count / total_tickets * 100) if total_tickets > 0 else 0, 1)
        in_progress_pct = round((in_progress_count / total_tickets * 100) if total_tickets > 0 else 0, 1)
        completed_pct = round((completed_count / total_tickets * 100) if total_tickets > 0 else 0, 1)

        on_time_starts = ServiceTicket.objects.filter(
            scheduled_date__gte=start_date,
            start_time__isnull=False,
            start_time__date__lte=F('scheduled_date')
        ).count()

        delayed_starts = ServiceTicket.objects.filter(
            scheduled_date__gte=start_date,
            start_time__isnull=False,
            start_time__date__gt=F('scheduled_date')
        ).count()

        # Technician utilization
        technicians = User.objects.filter(role='technician')
        active_technicians = technicians.filter(
            assigned_tickets__status__in=['In Progress', 'Not Started'],
            assigned_tickets__scheduled_date__gte=start_date
        ).distinct().count()

        # Average response time (time from request to assignment)
        assigned_tickets = ServiceTicket.objects.filter(
            assigned_at__isnull=False,
            request__request_date__gte=start_date
        )

        avg_response_time = 0
        if assigned_tickets.exists():
            total_response_time = sum(
                (ticket.assigned_at - ticket.request.request_date).total_seconds() / 3600
                for ticket in assigned_tickets
            )
            avg_response_time = total_response_time / assigned_tickets.count()

        return Response({
            'period_days': days,
            'completion_progress': {
                'total_tickets': total_tickets,
                'stages': {
                    'scheduled': f"{scheduled_pct}% scheduled",
                    'assigned': f"{assigned_pct}% assigned to technicians",
                    'in_progress': f"{in_progress_pct}% work in progress",
                    'completed': f"{completed_pct}% completed"
                },
                'overall_completion_rate': completed_pct
            },
            'scheduling_metrics': {
                'total_scheduled_tickets': total_tickets,
                'on_time_starts': on_time_starts,
                'delayed_starts': delayed_starts,
                'on_time_percentage': round((on_time_starts / total_tickets * 100) if total_tickets > 0 else 0, 1),
                'average_response_time_hours': round(avg_response_time, 1)
            },
            'resource_utilization': {
                'total_technicians': technicians.count(),
                'active_technicians': active_technicians,
                'utilization_rate': round((active_technicians / technicians.count() * 100) if technicians.count() > 0 else 0, 1)
            }
        })

    @action(detail=False, methods=['get'])
    def workflow_checklist_report(self, request):
        """Report on workflow compliance and checklist usage with completion progress"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)

        # Checklist completion rates
        total_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date)
        ).count()

        tickets_with_checklists = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            inspection__isnull=False
        ).count()

        completed_checklists = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            is_completed=True
        ).count()

        total_checklists = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date
        ).count()

        # Calculate completion stages for workflow
        inspection_scheduled = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date
        ).count()

        site_assessment_done = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            site_accessible__isnull=False
        ).count()

        safety_checks_done = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            safety_equipment_present__isnull=False,
            electrical_available__isnull=False
        ).count()

        final_approval = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            is_completed=True,
            recommendation='Approved'
        ).count()

        # Calculate percentages
        inspection_pct = round((inspection_scheduled / total_checklists * 100) if total_checklists > 0 else 0, 1)
        assessment_pct = round((site_assessment_done / total_checklists * 100) if total_checklists > 0 else 0, 1)
        safety_pct = round((safety_checks_done / total_checklists * 100) if total_checklists > 0 else 0, 1)
        approval_pct = round((final_approval / total_checklists * 100) if total_checklists > 0 else 0, 1)

        # Safety compliance from checklists
        safety_checks = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date
        ).aggregate(
            total=Count('id'),
            site_accessible=Count('id', filter=Q(site_accessible=True)),
            electrical_safe=Count('id', filter=Q(electrical_available=True, electrical_adequate=True)),
            safety_equipment=Count('id', filter=Q(safety_equipment_present=True))
        )

        # Approval rates
        approved_checklists = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            recommendation='Approved'
        ).count()

        return Response({
            'period_days': days,
            'completion_progress': {
                'total_checklists': total_checklists,
                'stages': {
                    'inspection_scheduled': f"{inspection_pct}% inspection scheduled",
                    'site_assessment': f"{assessment_pct}% site assessment completed",
                    'safety_checks': f"{safety_pct}% safety checks done",
                    'final_approval': f"{approval_pct}% final approval given"
                },
                'overall_completion_rate': approval_pct
            },
            'checklist_adoption': {
                'total_tickets': total_tickets,
                'tickets_with_checklists': tickets_with_checklists,
                'checklist_coverage': round((tickets_with_checklists / total_tickets * 100) if total_tickets > 0 else 0, 1),
                'completion_rate': round((completed_checklists / total_checklists * 100) if total_checklists > 0 else 0, 1)
            },
            'safety_compliance': {
                'total_inspections': safety_checks['total'],
                'site_access_compliance': round((safety_checks['site_accessible'] / safety_checks['total'] * 100) if safety_checks['total'] > 0 else 0, 1),
                'electrical_safety_compliance': round((safety_checks['electrical_safe'] / safety_checks['total'] * 100) if safety_checks['total'] > 0 else 0, 1),
                'ppe_compliance': round((safety_checks['safety_equipment'] / safety_checks['total'] * 100) if safety_checks['total'] > 0 else 0, 1)
            },
            'approval_rates': {
                'total_checklists': total_checklists,
                'approved': approved_checklists,
                'approval_rate': round((approved_checklists / total_checklists * 100) if total_checklists > 0 else 0, 1)
            }
        })

    @action(detail=False, methods=['get'])
    def inventory_resource_report(self, request):
        """Report on inventory management and resource availability with completion progress"""
        from inventory.models import InventoryItem, InventoryCategory

        # Inventory status
        total_items = InventoryItem.objects.count()
        in_stock = InventoryItem.objects.filter(quantity__gt=0).count()
        low_stock = InventoryItem.objects.filter(quantity__lte=0).count()
        out_of_stock = InventoryItem.objects.filter(quantity=0).count()

        # Calculate completion stages for inventory process
        ordered_items = InventoryItem.objects.filter(
            status='ordered'
        ).count()

        received_items = InventoryItem.objects.filter(
            status='received'
        ).count()

        inspected_items = InventoryItem.objects.filter(
            status='inspected'
        ).count()

        deployed_items = InventoryItem.objects.filter(
            status='deployed'
        ).count()

        # Calculate percentages
        ordered_pct = round((ordered_items / total_items * 100) if total_items > 0 else 0, 1)
        received_pct = round((received_items / total_items * 100) if total_items > 0 else 0, 1)
        inspected_pct = round((inspected_items / total_items * 100) if total_items > 0 else 0, 1)
        deployed_pct = round((deployed_items / total_items * 100) if total_items > 0 else 0, 1)

        # Stock levels
        items_below_minimum = InventoryItem.objects.filter(
            quantity__lt=F('minimum_stock')
        ).count()

        # Equipment utilization (simplified - would track actual usage)
        equipment_items = InventoryItem.objects.filter(item_type='equipment')
        available_equipment = equipment_items.filter(quantity__gt=0).count()

        # Parts availability for recent tickets
        recent_tickets = ServiceTicket.objects.filter(
            created_at__date__gte=timezone.now().date() - timezone.timedelta(days=30)
        )

        tickets_with_parts = 0
        for ticket in recent_tickets:
            # Simplified - would check if required parts were available
            tickets_with_parts += 1  # Assume parts were available

        return Response({
            'completion_progress': {
                'total_items': total_items,
                'stages': {
                    'ordered': f"{ordered_pct}% items ordered",
                    'received': f"{received_pct}% items received",
                    'inspected': f"{inspected_pct}% items inspected",
                    'deployed': f"{deployed_pct}% items deployed"
                },
                'overall_completion_rate': deployed_pct
            },
            'inventory_overview': {
                'total_items': total_items,
                'in_stock': in_stock,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
                'stock_availability_rate': round((in_stock / total_items * 100) if total_items > 0 else 0, 1)
            },
            'stock_management': {
                'items_below_minimum': items_below_minimum,
                'minimum_stock_compliance': round(((total_items - items_below_minimum) / total_items * 100) if total_items > 0 else 0, 1)
            },
            'equipment_utilization': {
                'total_equipment': equipment_items.count(),
                'available_equipment': available_equipment,
                'utilization_rate': round(((equipment_items.count() - available_equipment) / equipment_items.count() * 100) if equipment_items.count() > 0 else 0, 1)
            },
            'parts_availability': {
                'recent_tickets': recent_tickets.count(),
                'tickets_with_available_parts': tickets_with_parts,
                'parts_availability_rate': round((tickets_with_parts / recent_tickets.count() * 100) if recent_tickets.count() > 0 else 0, 1)
            }
        })

    @action(detail=False, methods=['get'])
    def communication_report(self, request):
        """Report on communication effectiveness and customer visibility with completion progress"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)

        # Service request updates
        total_requests = ServiceRequest.objects.filter(
            request_date__date__gte=start_date
        ).count()

        # Calculate completion stages for communication
        requests_acknowledged = ServiceRequest.objects.filter(
            request_date__date__gte=start_date,
            status__in=['Approved', 'In Progress', 'Scheduled']
        ).count()

        updates_provided = ServiceRequest.objects.filter(
            request_date__date__gte=start_date,
            updated_at__date__gt=F('request_date__date')
        ).count()

        resolved_requests = ServiceRequest.objects.filter(
            request_date__date__gte=start_date,
            status='Completed'
        ).count()

        feedback_received = ServiceRequest.objects.filter(
            request_date__date__gte=start_date,
            tickets__client_rating__isnull=False
        ).distinct().count()

        # Calculate percentages
        acknowledged_pct = round((requests_acknowledged / total_requests * 100) if total_requests > 0 else 0, 1)
        updates_pct = round((updates_provided / total_requests * 100) if total_requests > 0 else 0, 1)
        resolved_pct = round((resolved_requests / total_requests * 100) if total_requests > 0 else 0, 1)
        feedback_pct = round((feedback_received / total_requests * 100) if total_requests > 0 else 0, 1)

        requests_with_updates = ServiceRequest.objects.filter(
            request_date__date__gte=start_date,
            updated_at__date__gt=F('request_date__date')
        ).count()

        # Ticket status updates
        total_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date)
        ).count()

        tickets_with_updates = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            updated_at__date__gt=F('created_at__date')
        ).count()

        # Notification metrics (simplified - would track actual notifications)
        from notifications.models import Notification
        total_notifications = Notification.objects.filter(
            created_at__date__gte=start_date
        ).count()

        # Customer satisfaction (from completed tickets)
        completed_tickets = ServiceTicket.objects.filter(
            completed_date__date__gte=start_date,
            client_rating__isnull=False
        )

        satisfaction_data = completed_tickets.aggregate(
            total_rated=Count('id'),
            avg_rating=Avg('client_rating'),
            high_satisfaction=Count('id', filter=Q(client_rating__gte=4)),
            low_satisfaction=Count('id', filter=Q(client_rating__lte=2))
        )

        return Response({
            'period_days': days,
            'completion_progress': {
                'total_requests': total_requests,
                'stages': {
                    'acknowledged': f"{acknowledged_pct}% requests acknowledged",
                    'updates_provided': f"{updates_pct}% updates provided to customers",
                    'resolved': f"{resolved_pct}% requests resolved",
                    'feedback_received': f"{feedback_pct}% feedback received"
                },
                'overall_completion_rate': resolved_pct
            },
            'update_frequency': {
                'total_requests': total_requests,
                'requests_with_updates': requests_with_updates,
                'update_rate': round((requests_with_updates / total_requests * 100) if total_requests > 0 else 0, 1),
                'total_tickets': total_tickets,
                'tickets_with_updates': tickets_with_updates,
                'ticket_update_rate': round((tickets_with_updates / total_tickets * 100) if total_tickets > 0 else 0, 1)
            },
            'communication_metrics': {
                'total_notifications_sent': total_notifications,
                'notifications_per_day': round(total_notifications / days, 1)
            },
            'customer_satisfaction': {
                'total_rated_services': satisfaction_data['total_rated'],
                'average_rating': round(satisfaction_data['avg_rating'], 1) if satisfaction_data['avg_rating'] else None,
                'high_satisfaction_rate': round((satisfaction_data['high_satisfaction'] / satisfaction_data['total_rated'] * 100) if satisfaction_data['total_rated'] > 0 else 0, 1),
                'low_satisfaction_rate': round((satisfaction_data['low_satisfaction'] / satisfaction_data['total_rated'] * 100) if satisfaction_data['total_rated'] > 0 else 0, 1)
            }
        })

    @action(detail=False, methods=['get'])
    def performance_monitoring_report(self, request):
        """Report on key performance indicators and metrics with completion progress"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)

        # Service completion metrics
        total_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date)
        ).count()

        # Calculate completion stages for performance
        scheduled_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            scheduled_date__isnull=False
        ).count()

        started_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            start_time__isnull=False
        ).count()

        in_progress_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            status='In Progress'
        ).count()

        quality_checked = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            inspection__is_completed=True
        ).count()

        completed_tickets = ServiceTicket.objects.filter(
            Q(scheduled_date__gte=start_date) | Q(created_at__date__gte=start_date),
            status='Completed'
        ).count()

        # Calculate percentages
        scheduled_pct = round((scheduled_tickets / total_tickets * 100) if total_tickets > 0 else 0, 1)
        started_pct = round((started_tickets / total_tickets * 100) if total_tickets > 0 else 0, 1)
        in_progress_pct = round((in_progress_tickets / total_tickets * 100) if total_tickets > 0 else 0, 1)
        quality_pct = round((quality_checked / total_tickets * 100) if total_tickets > 0 else 0, 1)
        completed_pct = round((completed_tickets / total_tickets * 100) if total_tickets > 0 else 0, 1)

        on_time_completions = ServiceTicket.objects.filter(
            completed_date__date__gte=start_date,
            completed_date__date__lte=F('scheduled_date')
        ).count()

        # First-time fix rate (simplified - would track actual fixes)
        first_time_fixes = completed_tickets  # Assume all are first-time fixes for demo

        # Average completion time
        completed_with_times = ServiceTicket.objects.filter(
            completed_date__date__gte=start_date,
            start_time__isnull=False,
            end_time__isnull=False
        )

        avg_completion_time = 0
        if completed_with_times.exists():
            total_time = sum(
                (ticket.end_time - ticket.start_time).total_seconds() / 3600
                for ticket in completed_with_times
            )
            avg_completion_time = total_time / completed_with_times.count()

        # Customer satisfaction
        rated_services = ServiceTicket.objects.filter(
            completed_date__date__gte=start_date,
            client_rating__isnull=False
        )

        avg_satisfaction = rated_services.aggregate(avg=Avg('client_rating'))['avg']

        # Technician performance
        technicians = User.objects.filter(role='technician')
        active_technicians = technicians.filter(
            assigned_tickets__status__in=['In Progress', 'Completed'],
            assigned_tickets__scheduled_date__gte=start_date
        ).distinct()

        return Response({
            'period_days': days,
            'completion_progress': {
                'total_tickets': total_tickets,
                'stages': {
                    'scheduled': f"{scheduled_pct}% scheduled",
                    'started': f"{started_pct}% work started",
                    'in_progress': f"{in_progress_pct}% actively in progress",
                    'quality_check': f"{quality_pct}% quality checked",
                    'completed': f"{completed_pct}% completed"
                },
                'overall_completion_rate': completed_pct
            },
            'service_completion_kpis': {
                'total_tickets': total_tickets,
                'completed_tickets': completed_tickets,
                'completion_rate': round((completed_tickets / total_tickets * 100) if total_tickets > 0 else 0, 1),
                'on_time_completion_rate': round((on_time_completions / completed_tickets * 100) if completed_tickets > 0 else 0, 1),
                'first_time_fix_rate': round((first_time_fixes / completed_tickets * 100) if completed_tickets > 0 else 0, 1),
                'average_completion_time_hours': round(avg_completion_time, 1)
            },
            'customer_satisfaction': {
                'total_rated_services': rated_services.count(),
                'average_nps_score': round(avg_satisfaction * 2, 1) if avg_satisfaction else None,  # Convert 1-5 to 2-10 scale
                'satisfaction_trend': 'stable'  # Would calculate trend
            },
            'technician_performance': {
                'total_technicians': technicians.count(),
                'active_technicians': active_technicians.count(),
                'average_tickets_per_technician': round(total_tickets / technicians.count(), 1) if technicians.count() > 0 else 0
            }
        })

    @action(detail=False, methods=['get'])
    def safety_compliance_report(self, request):
        """Report on safety compliance and regulatory adherence with completion progress"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timezone.timedelta(days=days)

        # Inspection checklist safety data
        total_inspections = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date
        ).count()

        # Calculate completion stages for safety compliance
        inspections_scheduled = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date
        ).count()

        site_assessed = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            site_accessible__isnull=False
        ).count()

        safety_checks_completed = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            safety_equipment_present__isnull=False,
            electrical_available__isnull=False
        ).count()

        compliance_verified = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            is_completed=True
        ).count()

        approved_sites = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            is_completed=True,
            recommendation='Approved'
        ).count()

        # Calculate percentages
        scheduled_pct = round((inspections_scheduled / total_inspections * 100) if total_inspections > 0 else 0, 1)
        assessed_pct = round((site_assessed / total_inspections * 100) if total_inspections > 0 else 0, 1)
        safety_pct = round((safety_checks_completed / total_inspections * 100) if total_inspections > 0 else 0, 1)
        verified_pct = round((compliance_verified / total_inspections * 100) if total_inspections > 0 else 0, 1)
        approved_pct = round((approved_sites / total_inspections * 100) if total_inspections > 0 else 0, 1)

        safety_compliant = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            safety_equipment_present=True,
            electrical_available=True,
            site_accessible=True
        ).count()

        # PPE compliance (from checklists)
        ppe_compliant = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date,
            safety_equipment_present=True
        ).count()

        # Regulatory adherence (simplified - would track specific regulations)
        regulatory_checks = InspectionChecklist.objects.filter(
            created_at__date__gte=start_date
        ).aggregate(
            total=Count('id'),
            electrical_compliant=Count('id', filter=Q(electrical_available=True, electrical_adequate=True)),
            structural_compliant=Count('id', filter=Q(roof_condition__in=['Good', 'Excellent'])),
            hazard_free=Count('id', filter=Q(safety_hazards__isnull=True) | Q(safety_hazards=''))
        )

        # Incident tracking (simplified - would have incident model)
        reported_incidents = 0  # Would query incident model
        safety_training_completed = User.objects.filter(
            role='technician',
            date_joined__lte=start_date  # Simplified - assume trained if joined before period
        ).count()

        return Response({
            'period_days': days,
            'completion_progress': {
                'total_inspections': total_inspections,
                'stages': {
                    'inspection_scheduled': f"{scheduled_pct}% inspections scheduled",
                    'site_assessed': f"{assessed_pct}% sites assessed",
                    'safety_checks_completed': f"{safety_pct}% safety checks completed",
                    'compliance_verified': f"{verified_pct}% compliance verified",
                    'approved': f"{approved_pct}% sites approved"
                },
                'overall_completion_rate': approved_pct
            },
            'safety_compliance_overview': {
                'total_inspections': total_inspections,
                'safety_compliant_sites': safety_compliant,
                'overall_safety_compliance': round((safety_compliant / total_inspections * 100) if total_inspections > 0 else 0, 1)
            },
            'ppe_compliance': {
                'total_sites_checked': total_inspections,
                'ppe_compliant_sites': ppe_compliant,
                'ppe_compliance_rate': round((ppe_compliant / total_inspections * 100) if total_inspections > 0 else 0, 1)
            },
            'regulatory_adherence': {
                'electrical_safety_compliance': round((regulatory_checks['electrical_compliant'] / regulatory_checks['total'] * 100) if regulatory_checks['total'] > 0 else 0, 1),
                'structural_integrity_compliance': round((regulatory_checks['structural_compliant'] / regulatory_checks['total'] * 100) if regulatory_checks['total'] > 0 else 0, 1),
                'hazard_free_sites': round((regulatory_checks['hazard_free'] / regulatory_checks['total'] * 100) if regulatory_checks['total'] > 0 else 0, 1)
            },
            'safety_training_incidents': {
                'technicians_trained': safety_training_completed,
                'reported_safety_incidents': reported_incidents,
                'incident_rate': 0.0  # Would calculate per technician
            }
        })
    
    @action(detail=False, methods=['post'])
    def analyze_trends(self, request):
        """Analyze service trends"""
        service_type_id = request.data.get('service_type_id')
        trend_type = request.data.get('trend_type', 'monthly')
        months = int(request.data.get('months', 6))
        
        if not service_type_id:
            return Response({'error': 'service_type_id required'}, status=400)
        
        try:
            service_type = ServiceType.objects.get(id=service_type_id)
        except ServiceType.DoesNotExist:
            return Response({'error': 'Service type not found'}, status=404)
        
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=30 * months)
        
        # Get request data for the period
        requests = ServiceRequest.objects.filter(
            service_type=service_type,
            request_date__date__gte=start_date,
            request_date__date__lte=end_date
        ).order_by('request_date')
        
        if not requests.exists():
            return Response({'error': 'No data available for trend analysis'}, status=404)
        
        # Calculate monthly averages
        monthly_data = {}
        for request in requests:
            month_key = request.request_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = 0
            monthly_data[month_key] += 1
        
        # Calculate trend metrics
        request_counts = list(monthly_data.values())
        if len(request_counts) >= 2:
            avg_requests = sum(request_counts) / len(request_counts)
            
            # Simple growth rate calculation
            first_half = sum(request_counts[:len(request_counts)//2])
            second_half = sum(request_counts[len(request_counts)//2:])
            
            if first_half > 0:
                growth_rate = ((second_half - first_half) / first_half) * 100
            else:
                growth_rate = 0
            
            # Determine trend direction
            if growth_rate > 10:
                trend_direction = 'increasing'
            elif growth_rate < -10:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
            
            # Calculate standard deviation
            variance = sum((x - avg_requests) ** 2 for x in request_counts) / len(request_counts)
            std_dev = variance ** 0.5
            
            trend = ServiceTrend.objects.create(
                service_type=service_type,
                trend_type=trend_type,
                period_start=start_date,
                period_end=end_date,
                average_requests=avg_requests,
                growth_rate=growth_rate,
                trend_direction=trend_direction,
                standard_deviation=std_dev,
                confidence_interval={
                    'min': max(0, avg_requests - 2 * std_dev),
                    'max': avg_requests + 2 * std_dev
                }
            )
            
            serializer = self.get_serializer(trend)
            return Response(serializer.data)
        else:
            return Response({'error': 'Insufficient data for trend analysis'}, status=400)


class CoverageHeatmapViewSet(viewsets.ViewSet):
    """Coverage Heatmap - GIS-based visualization showing areas with high concentrations of past service requests."""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def service_density(self, request):
        """Get service request density data for coverage heatmap visualization."""
        # Get completed service requests with locations
        completed_requests = ServiceRequest.objects.filter(
            status='Completed'
        ).select_related('service_type', 'location')

        # Group by location and count requests
        density_data = {}
        for req in completed_requests:
            try:
                loc = req.location
                if loc.latitude and loc.longitude:
                    key = f"{loc.latitude:.4f},{loc.longitude:.4f}"
                    if key not in density_data:
                        density_data[key] = {
                            'lat': float(loc.latitude),
                            'lng': float(loc.longitude),
                            'count': 0,
                            'service_types': set(),
                            'address': loc.address
                        }
                    density_data[key]['count'] += 1
                    density_data[key]['service_types'].add(req.service_type.name)
            except ServiceLocation.DoesNotExist:
                pass

        # Convert to list and add service type info
        heatmap_points = []
        for point in density_data.values():
            point['service_types'] = list(point['service_types'])
            heatmap_points.append(point)

        return Response({
            'total_points': len(heatmap_points),
            'heatmap_data': heatmap_points,
            'max_density': max([p['count'] for p in heatmap_points]) if heatmap_points else 0
        })

    @action(detail=False, methods=['get'])
    def technician_coverage(self, request):
        """Get technician coverage areas for overlay on heatmap."""
        technicians = User.objects.filter(
            role='technician',
            status='active'
        ).values('id', 'username', 'current_latitude', 'current_longitude', 'is_available')

        coverage_areas = []
        for tech in technicians:
            if tech['current_latitude'] and tech['current_longitude']:
                coverage_areas.append({
                    'technician_id': tech['id'],
                    'name': tech['username'],
                    'center': [tech['current_latitude'], tech['current_longitude']],
                    'radius_km': 10  # Default 10km radius
                })

        return Response({
            'coverage_areas': coverage_areas,
            'total_technicians': len(coverage_areas)
        })


class ORSViewSet(viewsets.ViewSet):
    """ViewSet that proxies various OpenRouteService endpoints."""
    # Require authentication to prevent abuse of the server-side ORS API key.
    permission_classes = [permissions.IsAuthenticated]

    def _call_helper(self, helper_name, *args, **kwargs):
        """Convenience wrapper to import helpers dynamically."""
        from . import ors_utils
        helper = getattr(ors_utils, helper_name)
        return helper(*args, **kwargs)

    @action(detail=False, methods=['get'])
    def route(self, request):
        """Simple two-point routing via query parameters."""
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if not start or not end:
            return Response({'error': 'start and end parameters required'}, status=400)
        try:
            start_coords = tuple(map(float, start.split(',')))
            end_coords = tuple(map(float, end.split(',')))
        except ValueError:
            return Response({'error': 'invalid coordinate format'}, status=400)

        try:
            result = self._call_helper('get_route', start_coords, end_coords)
        except Exception as e:
            logger.error(f"ORS routing error for {start_coords} -> {end_coords}: {type(e).__name__}: {e}", exc_info=True)
            return Response({'error': 'routing request failed', 'details': str(e)}, status=502)
        return Response(result)

    @action(detail=False, methods=['post'])
    def directions(self, request):
        """POST wrapper for /directions endpoint.

        Expected JSON body includes:
          profile: str
          coordinates: [[lng,lat], ...]
          any other ORS options
        """
        data = request.data
        profile = data.get('profile')
        coords = data.get('coordinates')
        if not profile or not coords:
            return Response({'error': 'profile and coordinates required'}, status=400)
        try:
            result = self._call_helper('get_directions', coords, profile, **{k: v for k, v in data.items() if k not in ['profile', 'coordinates']})
        except Exception as e:
            return Response({'error': 'directions request failed', 'details': str(e)}, status=502)
        return Response(result)

    @action(detail=False, methods=['post'])
    def isochrones(self, request):
        data = request.data
        profile = data.get('profile')
        locations = data.get('locations')
        if not profile or not locations:
            return Response({'error': 'profile and locations required'}, status=400)
        try:
            result = self._call_helper('get_isochrones', locations, profile, **{k: v for k, v in data.items() if k not in ['profile', 'locations']})
        except Exception as e:
            return Response({'error': 'isochrones request failed', 'details': str(e)}, status=502)
        return Response(result)

    @action(detail=False, methods=['post'])
    def matrix(self, request):
        data = request.data
        profile = data.get('profile')
        locations = data.get('locations')
        if not profile or not locations:
            return Response({'error': 'profile and locations required'}, status=400)
        try:
            result = self._call_helper('get_matrix', locations, profile, **{k: v for k, v in data.items() if k not in ['profile', 'locations']})
        except Exception as e:
            return Response({'error': 'matrix request failed', 'details': str(e)}, status=502)
        return Response(result)

    @action(detail=False, methods=['post'])
    def snap(self, request):
        data = request.data
        profile = data.get('profile')
        coords = data.get('coordinates')
        if not profile or not coords:
            return Response({'error': 'profile and coordinates required'}, status=400)
        try:
            result = self._call_helper('snap_points', coords, profile, **{k: v for k, v in data.items() if k not in ['profile', 'coordinates']})
        except Exception as e:
            return Response({'error': 'snap request failed', 'details': str(e)}, status=502)
        return Response(result)
