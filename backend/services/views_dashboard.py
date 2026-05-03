from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q, Avg, F
from django.utils import timezone
from datetime import timedelta
import logging

from services.maintenance import process_maintenance_alerts
from services.models import (
    AfterSalesCase as FollowUpCase,
    MaintenanceSchedule,
    ServiceLocation,
    ServiceRequest,
    ServiceTicket,
)
from services.sla import evaluate_service_request_sla, evaluate_service_ticket_sla, serialize_sla_evaluation
from inventory.models import InventoryItem
from users.models import User
from users.rbac import (
    AFTER_SALES_VIEW_CAPABILITIES,
    SUPERVISOR_DASHBOARD_CAPABILITIES,
    TECHNICIAN_DASHBOARD_CAPABILITIES,
    is_admin_workspace_role,
    user_has_any_capability,
)

logger = logging.getLogger(__name__)


def _display_name(user):
    if not user:
        return None
    full_name = user.get_full_name().strip()
    return full_name or user.username


def _get_request_address(request):
    try:
        return request.location.address
    except ServiceLocation.DoesNotExist:
        return None


def _serialize_client_details(user, service_request=None):
    service_address = _get_request_address(service_request) if service_request else None
    return {
        'client_email': getattr(user, 'email', None) or None,
        'client_phone': getattr(user, 'phone', None) or None,
        'service_address': service_address or getattr(user, 'address', None) or None,
    }


def _serialize_active_technician_jobs(supervisor=None):
    """Get all active technician jobs with supervisor filter if provided"""
    # Get active tickets (In Progress or On Hold status)
    active_jobs = ServiceTicket.objects.select_related(
        'technician', 'request__client', 'request__service_type', 'request__location', 'supervisor'
    ).filter(
        status__in=['In Progress', 'On Hold'],
        technician__isnull=False,
        technician__is_active=True
    )
    
    # Filter by supervisor if provided (supervisor sees only their team's jobs)
    if supervisor:
        active_jobs = active_jobs.filter(supervisor=supervisor)
    
    # Order by most recent start time
    active_jobs = active_jobs.order_by('-start_time', '-id')[:20]
    
    return [
        {
            'id': job.id,
            'ticket_id': job.id,
            'technician': _display_name(job.technician),
            'technician_name': _display_name(job.technician),
            'client': _display_name(job.request.client),
            'service_type': job.request.service_type.name,
            'status': job.status,
            'priority': job.priority,
            'location': _get_request_address(job.request),
            'start_time': job.start_time.isoformat() if job.start_time else None,
            'progress': _calculate_job_progress(job),
            'sla_minutes_remaining': _calculate_sla_minutes_remaining(job),
        }
        for job in active_jobs
    ]


def _calculate_job_progress(ticket):
    """Calculate job progress percentage based on status and time elapsed"""
    if ticket.status == 'Completed':
        return 100
    elif ticket.status == 'In Progress':
        if ticket.start_time:
            # Estimate progress based on time elapsed vs estimated duration
            elapsed_minutes = (timezone.now() - ticket.start_time).total_seconds() / 60
            estimated_duration = 60  # Default estimate, could be from service type
            progress = min(int((elapsed_minutes / estimated_duration) * 100), 90)
            return max(progress, 10)
        return 50
    elif ticket.status == 'On Hold':
        return 30
    return 0


def _calculate_sla_minutes_remaining(ticket):
    """Calculate SLA minutes remaining for a ticket"""
    if not ticket.request or not ticket.request.service_type:
        return None
    
    service_type = ticket.request.service_type
    sla_hours = service_type.sla_hours if hasattr(service_type, 'sla_hours') else None
    
    if not sla_hours:
        return None
    
    # Get the reference time (request creation time or ticket assignment time)
    reference_time = ticket.request.request_date if ticket.request.request_date else timezone.now()
    
    # Calculate when SLA expires
    sla_expiry = reference_time + timedelta(hours=sla_hours)
    
    # Calculate minutes remaining
    minutes_remaining = (sla_expiry - timezone.now()).total_seconds() / 60
    
    return max(int(minutes_remaining), 0)


def _serialize_maintenance_queue(queryset):
    queue = []
    for schedule in queryset:
        queue.append({
            'id': schedule.id,
            'ticket_id': schedule.service_ticket_id,
            'client': _display_name(schedule.client),
            'service_type': schedule.service_type.name,
            'maintenance_profile': schedule.maintenance_profile,
            'maintenance_profile_label': schedule.get_maintenance_profile_display(),
            'status': schedule.status,
            'next_due_date': str(schedule.next_due_date),
            'notify_on_date': str(schedule.notify_on_date),
            'risk_level': schedule.risk_level,
            'risk_score': schedule.risk_score,
            'prediction_notes': schedule.prediction_notes,
            'location': _get_request_address(schedule.service_ticket.request),
            **_serialize_client_details(schedule.client, schedule.service_ticket.request),
        })
    return queue


def _build_sla_summary(*, service_requests=None, service_tickets=None, limit=8):
    now = timezone.now()
    summary = {
        'warning_count': 0,
        'overdue_count': 0,
        'approval_risk': 0,
        'assignment_risk': 0,
        'start_delay_risk': 0,
        'execution_risk': 0,
        'reschedule_risk': 0,
    }
    queue = []

    rule_to_summary_key = {
        'approval_delay': 'approval_risk',
        'assignment_delay': 'assignment_risk',
        'start_delay': 'start_delay_risk',
        'execution_delay': 'execution_risk',
        'reschedule_delay': 'reschedule_risk',
    }

    for service_request in service_requests or []:
        evaluation = evaluate_service_request_sla(service_request, now=now)
        if evaluation['state'] not in {'warning', 'overdue'}:
            continue

        summary_key = rule_to_summary_key.get(evaluation['rule'])
        if summary_key:
            summary[summary_key] += 1
        summary[f"{evaluation['state']}_count"] += 1
        queue.append({
            '_sort_state': 0 if evaluation['state'] == 'overdue' else 1,
            '_sort_due_at': evaluation.get('due_at') or now,
            'entity_type': 'request',
            'id': service_request.id,
            'client': _display_name(service_request.client),
            'service_type': service_request.service_type.name,
            'status': service_request.status,
            'requested_at': service_request.request_date.isoformat() if service_request.request_date else None,
            'sla': serialize_sla_evaluation(evaluation),
        })

    for ticket in service_tickets or []:
        evaluation = evaluate_service_ticket_sla(ticket, now=now)
        if evaluation['state'] not in {'warning', 'overdue'}:
            continue

        summary_key = rule_to_summary_key.get(evaluation['rule'])
        if summary_key:
            summary[summary_key] += 1
        summary[f"{evaluation['state']}_count"] += 1
        queue.append({
            '_sort_state': 0 if evaluation['state'] == 'overdue' else 1,
            '_sort_due_at': evaluation.get('due_at') or now,
            'entity_type': 'ticket',
            'id': ticket.id,
            'client': _display_name(ticket.request.client),
            'service_type': ticket.request.service_type.name,
            'status': ticket.status,
            'priority': ticket.priority,
            'assigned_technician': _display_name(ticket.technician) if ticket.technician else None,
            'scheduled_date': str(ticket.scheduled_date) if ticket.scheduled_date else None,
            'sla': serialize_sla_evaluation(evaluation),
        })

    queue.sort(key=lambda item: (item['_sort_state'], item['_sort_due_at']))
    for item in queue:
        item.pop('_sort_state', None)
        item.pop('_sort_due_at', None)

    return summary, queue[:limit]


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            requested_workspace = str(request.query_params.get('role') or '').strip()
            try:
                role = user.role
            except AttributeError:
                logger.error(f"User {user} does not have role attribute")
                return Response({'error': 'Invalid user - role attribute missing'}, status=400)

            if requested_workspace == 'follow_up':
                if (role == 'follow_up' or is_admin_workspace_role(role)) and user_has_any_capability(user, AFTER_SALES_VIEW_CAPABILITIES):
                    return self.get_follow_up_dashboard()
                return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)

            if requested_workspace == 'admin' and not is_admin_workspace_role(role):
                return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)

            if requested_workspace == 'supervisor':
                if (role == 'supervisor' or is_admin_workspace_role(role)) and user_has_any_capability(user, SUPERVISOR_DASHBOARD_CAPABILITIES):
                    return self.get_supervisor_dashboard()
                return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)

            if requested_workspace == 'technician':
                if role == 'technician' and user_has_any_capability(user, TECHNICIAN_DASHBOARD_CAPABILITIES):
                    return self.get_technician_dashboard()
                return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)

            if requested_workspace == 'client' and role != 'client':
                return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)

            if is_admin_workspace_role(role):
                return self.get_admin_dashboard()
            elif role == 'follow_up':
                if not user_has_any_capability(user, AFTER_SALES_VIEW_CAPABILITIES):
                    return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)
                return self.get_follow_up_dashboard()
            elif role == 'supervisor':
                if not user_has_any_capability(user, SUPERVISOR_DASHBOARD_CAPABILITIES):
                    return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)
                return self.get_supervisor_dashboard()
            elif role == 'technician':
                if not user_has_any_capability(user, TECHNICIAN_DASHBOARD_CAPABILITIES):
                    return Response({'error': 'You do not have access to the requested dashboard.'}, status=403)
                return self.get_technician_dashboard()
            elif role == 'client':
                return self.get_client_dashboard()
            else:
                return Response({'error': f'Invalid role: {role}'}, status=400)
        except Exception as e:
            logger.exception(f"Error in DashboardView.get: {str(e)}")
            return Response({'error': f'Dashboard error: {str(e)}'}, status=500)

    def get_admin_dashboard(self):
        """Admin dashboard with full system overview"""
        process_maintenance_alerts()

        # Service statistics
        total_tickets = ServiceTicket.objects.count()
        active_tickets = ServiceTicket.objects.filter(
            Q(status__in=['Not Started', 'In Progress', 'On Hold'])
        ).count()
        # completed_date is a DateTimeField, so use date range to compare dates
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        completed_today = ServiceTicket.objects.filter(
            completed_date__gte=today_start,
            completed_date__lt=today_end
        ).count()

        # Inventory statistics
        total_inventory = InventoryItem.objects.count()
        low_stock_items = InventoryItem.objects.filter(quantity__lte=F('minimum_stock')).count()
        out_of_stock = InventoryItem.objects.filter(quantity=0).count()

        # User statistics
        total_users = User.objects.count()
        active_technicians = User.objects.filter(role='technician', is_available=True).count()

        # Recent activity - use select_related to avoid N+1 queries
        # ServiceTicket has no created_at field, so use the request date or ticket id
        recent_tickets = ServiceTicket.objects.select_related(
            'request', 'request__client', 'request__service_type', 'technician'
        ).order_by('-id')[:5]
        # ServiceRequest uses request_date for creation
        recent_requests = ServiceRequest.objects.select_related(
            'client', 'service_type'
        ).order_by('-request_date')[:5]

        # Client schedule for upcoming assignment tasks - load all relationships
        client_schedule_tickets = ServiceTicket.objects.select_related(
            'request', 'request__client', 'request__service_type', 'technician'
        ).filter(
            status__in=['Not Started', 'In Progress'],
            scheduled_date__isnull=False
        ).order_by('scheduled_date', 'scheduled_time')[:20]
        sla_service_tickets = ServiceTicket.objects.select_related(
            'request', 'request__client', 'request__service_type', 'technician'
        ).filter(status__in=['Not Started', 'In Progress'])

        # Pending requests from clients (new)
        pending_requests = ServiceRequest.objects.select_related(
            'client', 'service_type'
        ).filter(status='Pending').order_by('request_date')[:10]
        sla_service_requests = ServiceRequest.objects.select_related(
            'client', 'service_type'
        ).filter(status='Pending')
        maintenance_schedules = MaintenanceSchedule.objects.select_related(
            'client',
            'service_type',
            'service_ticket__request__location',
        )
        active_maintenance = maintenance_schedules.exclude(status__in=['completed', 'dismissed'])
        sla_overview, sla_queue = _build_sla_summary(
            service_requests=sla_service_requests,
            service_tickets=sla_service_tickets,
        )

        return Response({
            'role': 'admin',
            'pending_requests': [
                {
                    'id': req.id,
                    'client': _display_name(req.client),
                    'service_type': req.service_type.name,
                    'status': req.status,
                    'request_date': req.request_date
                }
                for req in pending_requests
            ],
            'overview': {
                'total_tickets': total_tickets,
                'active_tickets': active_tickets,
                'completed_today': completed_today,
                'total_inventory': total_inventory,
                'low_stock_items': low_stock_items,
                'out_of_stock': out_of_stock,
                'total_users': total_users,
                'active_technicians': active_technicians,
                'due_soon_maintenance': active_maintenance.filter(status='due_soon').count(),
                'due_maintenance': active_maintenance.filter(status='due').count(),
            },
            'sla_overview': sla_overview,
            'sla_queue': sla_queue,
            'maintenance_queue': _serialize_maintenance_queue(
                active_maintenance.filter(status__in=['due_soon', 'due']).order_by('next_due_date')[:6]
            ),
            'client_schedule': [
                {
                    'id': ticket.id,
                    'client': _display_name(ticket.request.client),
                    'service_type': ticket.request.service_type.name,
                    'scheduled_date': ticket.scheduled_date,
                    'scheduled_time': str(ticket.scheduled_time) if ticket.scheduled_time else None,
                    'status': ticket.status,
                    'assigned_technician': _display_name(ticket.technician) if ticket.technician else None,
                    'location': _get_request_address(ticket.request)
                }
                for ticket in client_schedule_tickets
            ],
            'recent_activity': {
                'tickets': [
                    {
                        'id': ticket.id,
                        'client': _display_name(ticket.request.client),
                        'service_type': ticket.request.service_type.name,
                        'status': ticket.status,
                        # use request date for tickets
                        'created_at': ticket.request.request_date
                    } for ticket in recent_tickets
                ],
                'requests': [
                    {
                        'id': req.id,
                        'client': _display_name(req.client),
                        'service_type': req.service_type.name,
                        'status': req.status,
                        'created_at': req.request_date
                    } for req in recent_requests
                ]
            },
            'active_technician_jobs': _serialize_active_technician_jobs()
        })

    def get_follow_up_dashboard(self):
        """Service follow-up dashboard focused on callbacks, complaints, and revisits."""
        user = self.request.user
        today = timezone.now().date()
        week_ago = timezone.now() - timedelta(days=7)
        process_maintenance_alerts(reference_date=today)
        cases = FollowUpCase.objects.select_related(
            'service_ticket__request__client',
            'service_ticket__request__service_type',
            'assigned_to',
        )

        if user.role == 'follow_up':
            cases = cases.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))

        open_statuses = ['open', 'in_progress']
        case_breakdown = {
            row['case_type']: row['count']
            for row in cases.values('case_type').annotate(count=Count('id'))
        }

        unresolved_cases = cases.filter(status__in=open_statuses)
        follow_up_candidates = ServiceTicket.objects.select_related(
            'request__client', 'request__service_type'
        ).filter(status='Completed').exclude(after_sales_cases__isnull=False).order_by('-completed_date')[:5]
        maintenance_schedules = MaintenanceSchedule.objects.select_related(
            'client',
            'service_type',
            'service_ticket__request__location',
        ).exclude(status__in=['completed', 'dismissed'])

        return Response({
            'role': 'follow_up',
            'overview': {
                'total_cases': cases.count(),
                'open_cases': unresolved_cases.count(),
                'overdue_cases': unresolved_cases.filter(due_date__lt=today).count(),
                'resolved_this_week': cases.filter(resolved_at__gte=week_ago).count(),
                'completion_handoffs': unresolved_cases.filter(creation_source='completion_flow').count(),
                'follow_up_candidates': ServiceTicket.objects.filter(status='Completed').exclude(
                    after_sales_cases__isnull=False
                ).count(),
                'scheduled_maintenance': maintenance_schedules.count(),
                'maintenance_due_soon': maintenance_schedules.filter(status='due_soon').count(),
                'maintenance_due': maintenance_schedules.filter(status='due').count(),
            },
            'case_breakdown': case_breakdown,
            'maintenance_queue': _serialize_maintenance_queue(
                maintenance_schedules.filter(status__in=['due_soon', 'due']).order_by('next_due_date')[:8]
            ),
            'recent_cases': [
                {
                    'id': case.id,
                    'summary': case.summary,
                    'status': case.status,
                    'case_type': case.case_type,
                    'priority': case.priority,
                    'client': _display_name(case.client),
                    'service_type': case.service_ticket.request.service_type.name,
                    'assigned_to': _display_name(case.assigned_to) if case.assigned_to else None,
                    'created_by_name': _display_name(case.created_by) if case.created_by else None,
                    'creation_source': case.creation_source,
                    'creation_source_label': case.get_creation_source_display(),
                    'due_date': str(case.due_date) if case.due_date else None,
                    **_serialize_client_details(case.client, case.service_ticket.request),
                }
                for case in cases.order_by('-created_at')[:8]
            ],
            'follow_up_candidates': [
                {
                    'ticket_id': ticket.id,
                    'client': _display_name(ticket.request.client),
                    'service_type': ticket.request.service_type.name,
                    'completed_date': ticket.completed_date.isoformat() if ticket.completed_date else None,
                    **_serialize_client_details(ticket.request.client, ticket.request),
                }
                for ticket in follow_up_candidates
            ],
        })

    def get_supervisor_dashboard(self):
        """Supervisor dashboard with team management focus"""
        user = self.request.user
        thirty_days_ago = timezone.now() - timedelta(days=30)

        # Team tickets - with proper relationships loaded
        team_tickets = ServiceTicket.objects.select_related(
            'request', 'request__client', 'request__service_type', 'technician', 'supervisor'
        ).filter(
            Q(supervisor=user) | Q(supervisor__isnull=True)
        )
        active_team_tickets = team_tickets.filter(
            Q(status__in=['Not Started', 'In Progress', 'On Hold'])
        ).count()

        # Technician performance - OPTIMIZED: Single annotated query instead of N+1 loop
        technician_stats = list(
            User.objects.filter(role='technician')
            .annotate(
                tickets_completed=Count(
                    'assigned_tickets',
                    filter=Q(
                        assigned_tickets__status='Completed',
                        assigned_tickets__completed_date__gte=thirty_days_ago
                    )
                )
            )
            .values('id', 'username', 'first_name', 'last_name', 'is_available', 'tickets_completed')
            .order_by('-tickets_completed')
        )

        for technician in technician_stats:
            full_name = f"{technician.get('first_name', '')} {technician.get('last_name', '')}".strip()
            technician['name'] = full_name or technician['username']

        # Pending approvals
        pending_requests_count = ServiceRequest.objects.filter(status='Pending').count()
        sla_overview, sla_queue = _build_sla_summary(service_tickets=team_tickets)

        return Response({
            'role': 'supervisor',
            'overview': {
                'team_tickets': team_tickets.count(),
                'active_team_tickets': active_team_tickets,
                'pending_approvals': pending_requests_count,
                'total_technicians': len(technician_stats),
            },
            'sla_overview': sla_overview,
            'sla_queue': sla_queue,
            'technician_performance': technician_stats,
            'recent_tickets': [
                {
                    'id': ticket.id,
                    'technician': _display_name(ticket.technician) if ticket.technician else None,
                    'client': _display_name(ticket.request.client),
                    'status': ticket.status,
                    'priority': ticket.priority,
                    'scheduled_date': str(ticket.scheduled_date) if ticket.scheduled_date else None
                } for ticket in team_tickets.order_by('-id')[:10]
            ],
            'active_technician_jobs': _serialize_active_technician_jobs(supervisor=user)
        })

    def get_technician_dashboard(self):
        """Technician dashboard with assigned work focus"""
        user = self.request.user
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # My tickets - load all relationships upfront to avoid N+1
        my_tickets = ServiceTicket.objects.select_related(
            'request', 'request__client', 'request__service_type', 'request__location'
        ).filter(
            Q(technician=user) | Q(crew_assignments__technician=user)
        ).distinct()
        active_tickets = my_tickets.filter(
            Q(status__in=['Not Started', 'In Progress', 'On Hold'])
        )
        completed_this_month = my_tickets.filter(
            status='Completed',
            completed_date__gte=month_start
        ).count()

        # Today's schedule
        today = timezone.now().date()
        todays_tickets = my_tickets.filter(scheduled_date=today)

        # Inventory access (read-only for technicians)
        low_stock_items_qs = InventoryItem.objects.filter(quantity__lte=F('minimum_stock'))[:5]
        low_stock_alerts = [
            {
                'id': item.id,
                'name': item.name,
                'available_quantity': item.available_quantity if hasattr(item, 'available_quantity') else item.quantity,
                'minimum_stock': item.minimum_stock
            } for item in low_stock_items_qs
        ]

        return Response({
            'role': 'technician',
            'overview': {
                'total_assigned': my_tickets.count(),
                'active_tickets': active_tickets.count(),
                'completed_this_month': completed_this_month,
                'todays_schedule': todays_tickets.count(),
            },
            'active_work': [
                {
                    'id': ticket.id,
                    'client': _display_name(ticket.request.client),
                    'service_type': ticket.request.service_type.name,
                    'status': ticket.status,
                    'scheduled_date': str(ticket.scheduled_date) if ticket.scheduled_date else None,
                    'priority': ticket.priority
                } for ticket in active_tickets.order_by('scheduled_date')[:5]
            ],
            'todays_schedule': [
                {
                    'id': ticket.id,
                    'client': _display_name(ticket.request.client),
                    'service_type': ticket.request.service_type.name,
                    'scheduled_time': str(ticket.scheduled_time) if ticket.scheduled_time else None,
                    'location': _get_request_address(ticket.request),
                } for ticket in todays_tickets.order_by('scheduled_time')
            ],
            'low_stock_alerts': low_stock_alerts
        })

    def get_client_dashboard(self):
        """Client dashboard with service request focus"""
        try:
            user = self.request.user

            # My service requests with safe access
            try:
                my_requests = ServiceRequest.objects.select_related(
                    'client', 'service_type'
                ).filter(client=user)
                active_requests = my_requests.filter(Q(status__in=['Pending', 'Approved']))
                pending_requests = my_requests.filter(status='Pending')
                requests_count = my_requests.count()
                active_req_count = active_requests.count()
            except Exception as e:
                logger.warning(f"Error fetching requests for {user}: {str(e)}")
                requests_count = 0
                active_req_count = 0
                active_requests = []
                pending_requests = []

            # My tickets with safe access
            try:
                my_tickets = ServiceTicket.objects.filter(request__client=user).select_related(
                    'request', 'request__service_type', 'technician'
                )
                active_tickets = my_tickets.filter(Q(status__in=['Not Started', 'In Progress', 'On Hold']))
                on_hold_tickets = my_tickets.filter(status='On Hold')
                completed_tickets_qs = my_tickets.filter(status='Completed').order_by('-completed_date')[:5]
                tickets_count = my_tickets.count()
                active_tickets_count = active_tickets.count()
            except Exception as e:
                logger.warning(f"Error fetching tickets for {user}: {str(e)}")
                tickets_count = 0
                active_tickets_count = 0
                active_tickets = []
                on_hold_tickets = []
                completed_tickets_qs = []

            # Status breakdown with safe counts
            status_stats = {}
            try:
                status_stats['pending'] = my_requests.filter(status='Pending').count()
                status_stats['approved'] = my_requests.filter(status='Approved').count()
                status_stats['in_progress'] = my_tickets.filter(status='In Progress').count()
                status_stats['completed'] = my_tickets.filter(status='Completed').count()
                status_stats['on_hold'] = on_hold_tickets.count() if 'on_hold_tickets' in locals() else 0
            except Exception as e:
                logger.warning(f"Error counting statuses: {str(e)}")
                status_stats = {'pending': 0, 'approved': 0, 'in_progress': 0, 'completed': 0, 'on_hold': 0}

            # Calculate rating safely
            avg_rating = None
            total_rated = 0
            try:
                completed_with_rating = my_tickets.filter(status='Completed', client_rating__isnull=False)
                total_rated = completed_with_rating.count()
                if total_rated > 0:
                    rating_agg = completed_with_rating.aggregate(avg=Avg('client_rating'))
                    avg_rating = round(rating_agg['avg'], 1) if rating_agg['avg'] else None
            except Exception as e:
                logger.warning(f"Error calculating rating: {str(e)}")

            # Build active requests list
            active_requests_list = []
            try:
                for req in active_requests.order_by('-request_date')[:3]:
                    try:
                        active_requests_list.append({
                            'id': req.id,
                            'service_type': req.service_type.name if req.service_type else 'Unknown',
                            'status': req.status,
                            'created_at': str(req.request_date.isoformat()) if req.request_date else None,
                            'description': (req.description[:100] + '...') if len(req.description) > 100 else req.description
                        })
                    except AttributeError:
                        logger.warning(f"Missing service_type for request {req.id}")
            except Exception as e:
                logger.warning(f"Error building active requests list: {str(e)}")

            # Build active tickets list  
            active_tickets_list = []
            try:
                for ticket in active_tickets.order_by('scheduled_date')[:3]:
                    try:
                        tech_username = 'Not assigned'
                        if ticket.technician:
                            tech_username = _display_name(ticket.technician)
                        service_name = 'Unknown'
                        if ticket.request and ticket.request.service_type:
                            service_name = ticket.request.service_type.name
                        
                        active_tickets_list.append({
                            'id': ticket.id,
                            'service_type': service_name,
                            'technician': tech_username,
                            'status': ticket.status,
                            'scheduled_date': str(ticket.scheduled_date) if ticket.scheduled_date else None,
                            'priority': ticket.priority
                        })
                    except Exception as inner_e:
                        logger.warning(f"Error processing ticket {ticket.id}: {str(inner_e)}")
            except Exception as e:
                logger.warning(f"Error building active tickets list: {str(e)}")

            # Build history list
            recent_history_list = []
            try:
                for ticket in completed_tickets_qs:
                    try:
                        tech_username = _display_name(ticket.technician) if ticket.technician else 'N/A'
                        service_name = 'Unknown'
                        if ticket.request and ticket.request.service_type:
                            service_name = ticket.request.service_type.name
                        
                        recent_history_list.append({
                            'id': ticket.id,
                            'service_type': service_name,
                            'completed_date': str(ticket.completed_date.isoformat()) if ticket.completed_date else None,
                            'technician': tech_username,
                            'rating': ticket.client_rating
                        })
                    except Exception as inner_e:
                        logger.warning(f"Error processing history ticket {ticket.id}: {str(inner_e)}")
            except Exception as e:
                logger.warning(f"Error building history list: {str(e)}")

            # Alerts and recommendations
            alerts = []
            recommendations = []
            
            try:
                if pending_requests.count() > 0:
                    alerts.append({
                        'type': 'warning',
                        'message': f'You have {pending_requests.count()} request(s) waiting for approval'
                    })
                if on_hold_tickets.count() > 0:
                    alerts.append({
                        'type': 'alert',
                        'message': f'{on_hold_tickets.count()} service(s) are on hold - check for details'
                    })
                if active_tickets_count == 0 and active_req_count == 0:
                    recommendations.append({
                        'message': 'No active services - Schedule maintenance or request evaluation',
                        'action': 'Create Request'
                    })
                if requests_count > 10:
                    recommendations.append({
                        'message': 'Consider a service plan for better coverage',
                        'action': 'Learn More'
                    })
            except Exception as e:
                logger.warning(f"Error building alerts: {str(e)}")

            return Response({
                'role': 'client',
                'overview': {
                    'total_requests': requests_count,
                    'active_requests': active_req_count,
                    'active_tickets': active_tickets_count,
                    'completed_services': my_tickets.filter(status='Completed').count() if 'my_tickets' in locals() else 0,
                },
                'status_breakdown': status_stats,
                'performance': {
                    'avg_rating': avg_rating,
                    'total_rated': total_rated
                },
                'active_requests': active_requests_list,
                'active_tickets': active_tickets_list,
                'recent_history': recent_history_list,
                'alerts': alerts,
                'recommendations': recommendations
            })
        except Exception as e:
            logger.exception(f"Critical error in get_client_dashboard: {str(e)}")
            return Response({
                'error': f'Error fetching client dashboard: {str(e)}',
                'role': 'client',
                'overview': {'total_requests': 0, 'active_requests': 0, 'active_tickets': 0, 'completed_services': 0},
                'status_breakdown': {},
                'performance': {'avg_rating': None, 'total_rated': 0},
                'active_requests': [],
                'active_tickets': [],
                'recent_history': [],
                'alerts': [],
                'recommendations': []
            }, status=200)  # Return 200 not 500 to show partial data is better than nothing
