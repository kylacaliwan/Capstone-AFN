from datetime import datetime, time, timedelta

from django.utils import timezone


SLA_STATE_INACTIVE = 'inactive'
SLA_STATE_HEALTHY = 'healthy'
SLA_STATE_WARNING = 'warning'
SLA_STATE_OVERDUE = 'overdue'
SLA_STATE_PAUSED = 'paused'

SLA_RULE_LABELS = {
    'approval_delay': 'Approval delay',
    'assignment_delay': 'Assignment delay',
    'start_delay': 'Start delay',
    'execution_delay': 'Execution delay',
    'reschedule_delay': 'Reschedule delay',
}

TIME_SLOT_DEFAULTS = {
    'morning': time(hour=9, minute=0),
    'midday': time(hour=12, minute=0),
    'afternoon': time(hour=15, minute=0),
    'evening': time(hour=18, minute=0),
}

APPROVAL_WARNING_AFTER = timedelta(hours=4)
APPROVAL_OVERDUE_AFTER = timedelta(hours=8)
ASSIGNMENT_WARNING_AFTER = timedelta(hours=2)
ASSIGNMENT_OVERDUE_AFTER = timedelta(hours=6)
START_WARNING_AFTER = timedelta(minutes=15)
START_OVERDUE_AFTER = timedelta(minutes=60)
EXECUTION_WARNING_MULTIPLIER = 1.5
EXECUTION_OVERDUE_MULTIPLIER = 2
RESCHEDULE_WARNING_AFTER = timedelta(hours=4)
RESCHEDULE_OVERDUE_AFTER = timedelta(hours=12)


def _minutes_until(reference_time, target_time):
    if reference_time is None or target_time is None:
        return None

    seconds = (target_time - reference_time).total_seconds()
    if seconds <= 0:
        return 0
    return int(seconds // 60)


def _minutes_overdue(reference_time, target_time):
    if reference_time is None or target_time is None or reference_time <= target_time:
        return 0
    return int((reference_time - target_time).total_seconds() // 60)


def _build_result(
    *,
    state,
    label,
    rule=None,
    warning_at=None,
    due_at=None,
    action_required=None,
    now=None,
):
    if now is None:
        now = timezone.now()

    breached_at = due_at if state == SLA_STATE_OVERDUE and due_at else None
    return {
        'state': state,
        'rule': rule,
        'rule_label': SLA_RULE_LABELS.get(rule) if rule else None,
        'label': label,
        'warning_at': warning_at,
        'due_at': due_at,
        'breached_at': breached_at,
        'minutes_to_breach': _minutes_until(now, due_at),
        'minutes_overdue': _minutes_overdue(now, due_at),
        'action_required': action_required,
        'is_active': state not in {SLA_STATE_INACTIVE, SLA_STATE_PAUSED},
    }


def _build_timed_result(*, rule, label_prefix, warning_at, due_at, action_required, now=None):
    if now is None:
        now = timezone.now()

    if due_at and now >= due_at:
        state = SLA_STATE_OVERDUE
        label = f'{label_prefix} overdue'
    elif warning_at and now >= warning_at:
        state = SLA_STATE_WARNING
        label = f'{label_prefix} approaching SLA breach'
    else:
        state = SLA_STATE_HEALTHY
        label = f'{label_prefix} within SLA'

    return _build_result(
        state=state,
        rule=rule,
        label=label,
        warning_at=warning_at,
        due_at=due_at,
        action_required=action_required,
        now=now,
    )


def _serialize_datetime(value):
    return value.isoformat() if value else None


def _resolve_scheduled_start(ticket):
    if not getattr(ticket, 'scheduled_date', None):
        return None

    scheduled_time = getattr(ticket, 'scheduled_time', None)
    if scheduled_time is None:
        scheduled_time = TIME_SLOT_DEFAULTS.get(getattr(ticket, 'scheduled_time_slot', None))
    if scheduled_time is None:
        scheduled_time = TIME_SLOT_DEFAULTS['morning']

    naive_start = datetime.combine(ticket.scheduled_date, scheduled_time)
    current_timezone = timezone.get_current_timezone()
    if timezone.is_naive(naive_start):
        return timezone.make_aware(naive_start, current_timezone)
    return naive_start.astimezone(current_timezone)


def serialize_sla_evaluation(evaluation):
    return {
        **evaluation,
        'warning_at': _serialize_datetime(evaluation.get('warning_at')),
        'due_at': _serialize_datetime(evaluation.get('due_at')),
        'breached_at': _serialize_datetime(evaluation.get('breached_at')),
    }


def evaluate_service_request_sla(service_request, *, now=None):
    if now is None:
        now = timezone.now()

    if service_request.status in {'Completed', 'Cancelled'}:
        return _build_result(
            state=SLA_STATE_PAUSED,
            label='Request SLA paused',
            now=now,
        )

    if service_request.status != 'Pending':
        return _build_result(
            state=SLA_STATE_INACTIVE,
            label='No active request SLA',
            now=now,
        )

    request_time = service_request.request_date or now
    return _build_timed_result(
        rule='approval_delay',
        label_prefix='Approval',
        warning_at=request_time + APPROVAL_WARNING_AFTER,
        due_at=request_time + APPROVAL_OVERDUE_AFTER,
        action_required='Review request',
        now=now,
    )


def evaluate_service_ticket_sla(service_ticket, *, now=None):
    if now is None:
        now = timezone.now()

    if service_ticket.status in {'Completed', 'Cancelled'}:
        return _build_result(
            state=SLA_STATE_PAUSED,
            label='Ticket SLA paused',
            now=now,
        )

    if service_ticket.reschedule_requested:
        reschedule_time = service_ticket.reschedule_requested_at or service_ticket.updated_at or now
        return _build_timed_result(
            rule='reschedule_delay',
            label_prefix='Reschedule response',
            warning_at=reschedule_time + RESCHEDULE_WARNING_AFTER,
            due_at=reschedule_time + RESCHEDULE_OVERDUE_AFTER,
            action_required='Review reschedule request',
            now=now,
        )

    if service_ticket.status == 'Not Started' and not service_ticket.technician_id:
        created_time = service_ticket.created_at or now
        return _build_timed_result(
            rule='assignment_delay',
            label_prefix='Assignment',
            warning_at=created_time + ASSIGNMENT_WARNING_AFTER,
            due_at=created_time + ASSIGNMENT_OVERDUE_AFTER,
            action_required='Assign technician',
            now=now,
        )

    if service_ticket.status == 'Not Started' and service_ticket.technician_id:
        scheduled_start = _resolve_scheduled_start(service_ticket)
        return _build_timed_result(
            rule='start_delay',
            label_prefix='Start time',
            warning_at=scheduled_start + START_WARNING_AFTER if scheduled_start else None,
            due_at=scheduled_start + START_OVERDUE_AFTER if scheduled_start else None,
            action_required='Start work',
            now=now,
        )

    if service_ticket.status == 'In Progress':
        service_type = getattr(getattr(service_ticket, 'request', None), 'service_type', None)
        estimated_minutes = max(
            int(getattr(service_type, 'estimated_duration', 60) or 60),
            1,
        )
        execution_start = (
            service_ticket.start_time
            or service_ticket.updated_at
            or service_ticket.assigned_at
            or service_ticket.created_at
            or now
        )
        return _build_timed_result(
            rule='execution_delay',
            label_prefix='Execution',
            warning_at=execution_start + timedelta(minutes=estimated_minutes * EXECUTION_WARNING_MULTIPLIER),
            due_at=execution_start + timedelta(minutes=estimated_minutes * EXECUTION_OVERDUE_MULTIPLIER),
            action_required='Complete work',
            now=now,
        )

    return _build_result(
        state=SLA_STATE_INACTIVE,
        label='No active ticket SLA',
        now=now,
    )
