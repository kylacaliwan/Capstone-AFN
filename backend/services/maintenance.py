from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from notifications.models import Notification

from .models import AfterSalesCase as FollowUpCase
from .models import InspectionChecklist, MaintenanceSchedule, ServiceTicket


DEFAULT_FOLLOW_UP_WINDOW_DAYS = 14
COMPLETION_FOLLOW_UP_DEFAULT_OFFSETS = {
    'complaint': 1,
    'revisit': 2,
    'warranty': 3,
    'feedback': 3,
    'follow_up': 2,
}

MAINTENANCE_RULES = {
    'commercial_area': {
        'label': 'Commercial Area',
        'interval_days': 90,
    },
    'dust_free_area': {
        'label': 'Dust-Free Area',
        'interval_days': 180,
    },
    'standard_area': {
        'label': 'Standard Area',
        'interval_days': 120,
    },
}


def get_maintenance_rule(profile):
    return MAINTENANCE_RULES.get(profile, MAINTENANCE_RULES['standard_area'])


def resolve_interval_days(profile, override_days=None):
    if override_days:
        return int(override_days)
    return get_maintenance_rule(profile)['interval_days']


def evaluate_schedule_status(schedule, reference_date=None):
    reference_date = reference_date or timezone.localdate()

    if schedule.status in {'completed', 'dismissed'}:
        return schedule.status
    if reference_date >= schedule.next_due_date:
        return 'due'
    if reference_date >= schedule.notify_on_date:
        return 'due_soon'
    return 'scheduled'


def calculate_maintenance_risk(ticket, inspection=None, reference_date=None):
    reference_date = reference_date or timezone.localdate()
    if inspection is None:
        try:
            inspection = ticket.inspection
        except InspectionChecklist.DoesNotExist:
            inspection = None
    service_type = ticket.request.service_type
    client = ticket.request.client

    base_scores = {
        'commercial_area': 65,
        'standard_area': 50,
        'dust_free_area': 35,
    }
    base_score = base_scores.get(getattr(inspection, 'maintenance_profile', None), 45)

    one_year_ago = reference_date - timedelta(days=365)
    related_cases = FollowUpCase.objects.filter(
        client=client,
        service_ticket__request__service_type=service_type,
        created_at__date__gte=one_year_ago,
    ).exclude(service_ticket=ticket)

    complaint_cases = related_cases.filter(case_type='complaint').count()
    revisit_cases = related_cases.filter(case_type='revisit').count()
    warranty_cases = related_cases.filter(case_type='warranty').count()
    prior_completed = ServiceTicket.objects.filter(
        request__client=client,
        request__service_type=service_type,
        status='Completed',
        completed_date__date__gte=one_year_ago,
    ).exclude(pk=ticket.pk).count()
    overdue_schedules = MaintenanceSchedule.objects.filter(
        client=client,
        service_type=service_type,
        next_due_date__lt=reference_date,
        status__in=['due', 'due_soon'],
    ).exclude(service_ticket=ticket).count()

    score = base_score
    if service_type.estimated_duration >= 120:
        score += 8
    score += min(prior_completed * 4, 12)
    score += complaint_cases * 8
    score += revisit_cases * 6
    score += warranty_cases * 5
    score += overdue_schedules * 10
    score = float(min(score, 100))

    if score >= 70:
        risk_level = 'high'
    elif score >= 45:
        risk_level = 'normal'
    else:
        risk_level = 'low'

    signals = []
    if complaint_cases:
        signals.append(f"{complaint_cases} complaint case(s)")
    if revisit_cases:
        signals.append(f"{revisit_cases} revisit case(s)")
    if warranty_cases:
        signals.append(f"{warranty_cases} warranty case(s)")
    if overdue_schedules:
        signals.append(f"{overdue_schedules} overdue maintenance cycle(s)")
    if not signals:
        signals.append('stable service history')

    notes = (
        f"Predicted {risk_level} maintenance risk based on "
        f"{service_type.name.lower()} service history, a {service_type.estimated_duration}-minute service baseline, "
        f"and {', '.join(signals)} in the last 12 months."
    )
    return {
        'risk_level': risk_level,
        'risk_score': score,
        'prediction_notes': notes,
    }


def evaluate_warranty_status(ticket, reference_date=None):
    reference_date = reference_date or timezone.localdate()

    if ticket.warranty_status == 'void':
        return 'void'
    if not ticket.warranty_period_days or not ticket.warranty_end_date:
        return 'not_applicable'
    if reference_date <= ticket.warranty_end_date:
        return 'active'
    return 'expired'


def sync_ticket_warranty(ticket, reference_date=None):
    reference_date = reference_date or timezone.localdate()
    try:
        inspection = ticket.inspection
    except InspectionChecklist.DoesNotExist:
        inspection = None

    desired_values = {
        'warranty_status': 'not_applicable',
        'warranty_period_days': None,
        'warranty_start_date': None,
        'warranty_end_date': None,
        'warranty_notes': None,
    }

    if inspection and inspection.warranty_provided and inspection.warranty_period_days:
        start_date = (ticket.completed_date or ticket.end_time or timezone.now()).date()
        period_days = int(inspection.warranty_period_days)
        end_date = start_date + timedelta(days=period_days)
        desired_values.update({
            'warranty_period_days': period_days,
            'warranty_start_date': start_date,
            'warranty_end_date': end_date,
            'warranty_notes': inspection.warranty_notes or inspection.additional_notes,
            'warranty_status': 'active' if reference_date <= end_date else 'expired',
        })

    update_fields = []
    for field_name, value in desired_values.items():
        if getattr(ticket, field_name) != value:
            setattr(ticket, field_name, value)
            update_fields.append(field_name)

    if update_fields:
        update_fields.append('updated_at')
        ticket.save(update_fields=update_fields)

    return ticket


def sync_maintenance_schedule(ticket, reference_date=None):
    try:
        inspection = ticket.inspection
    except InspectionChecklist.DoesNotExist:
        return None

    if not inspection.maintenance_required or not inspection.maintenance_profile:
        return None

    reference_date = reference_date or timezone.localdate()
    last_service_date = (ticket.completed_date or ticket.end_time or timezone.now()).date()
    interval_days = resolve_interval_days(
        inspection.maintenance_profile,
        inspection.maintenance_interval_days,
    )
    follow_up_window_days = min(DEFAULT_FOLLOW_UP_WINDOW_DAYS, interval_days)
    next_due_date = last_service_date + timedelta(days=interval_days)
    notify_on_date = next_due_date - timedelta(days=follow_up_window_days)
    risk_data = calculate_maintenance_risk(
        ticket,
        inspection=inspection,
        reference_date=reference_date,
    )

    schedule, _ = MaintenanceSchedule.objects.update_or_create(
        service_ticket=ticket,
        defaults={
            'client': ticket.request.client,
            'service_type': ticket.request.service_type,
            'maintenance_profile': inspection.maintenance_profile,
            'interval_days': interval_days,
            'follow_up_window_days': follow_up_window_days,
            'last_service_date': last_service_date,
            'next_due_date': next_due_date,
            'notify_on_date': notify_on_date,
            'maintenance_notes': inspection.maintenance_notes or inspection.additional_notes,
            'risk_level': risk_data['risk_level'],
            'risk_score': risk_data['risk_score'],
            'prediction_notes': risk_data['prediction_notes'],
        },
    )

    schedule.status = evaluate_schedule_status(schedule, reference_date=reference_date)
    schedule.save(update_fields=['status', 'updated_at'])
    return schedule


def _build_completion_follow_up_summary(ticket, case_type):
    service_name = ticket.request.service_type.name if ticket.request.service_type else 'service'
    summary_map = {
        'follow_up': f'Post-service follow-up for ticket #{ticket.id}',
        'complaint': f'Complaint review needed for ticket #{ticket.id}',
        'warranty': f'Warranty handoff needed for ticket #{ticket.id}',
        'revisit': f'Revisit needed for ticket #{ticket.id}',
        'feedback': f'Capture customer feedback for ticket #{ticket.id}',
    }
    return summary_map.get(case_type, f'After-sales handoff for {service_name} ticket #{ticket.id}')


def _build_completion_follow_up_details(ticket, inspection, case_type):
    details = []

    if inspection.follow_up_details:
        details.append(str(inspection.follow_up_details).strip())
    if inspection.additional_notes:
        details.append(f"Technician notes: {str(inspection.additional_notes).strip()}")
    if case_type == 'warranty' and inspection.warranty_notes:
        details.append(f"Warranty notes: {str(inspection.warranty_notes).strip()}")
    if inspection.maintenance_required and inspection.maintenance_notes:
        details.append(f"Maintenance context: {str(inspection.maintenance_notes).strip()}")

    return "\n\n".join(item for item in details if item)


def _default_completion_follow_up_due_date(ticket, case_type, reference_date):
    if case_type == 'warranty' and ticket.warranty_end_date:
        return ticket.warranty_end_date

    offset_days = COMPLETION_FOLLOW_UP_DEFAULT_OFFSETS.get(case_type, 2)
    return reference_date + timedelta(days=offset_days)


def _notify_completion_follow_up_case(case, *, created):
    User = get_user_model()
    recipients = User.objects.filter(role='follow_up', status='active').order_by('id')
    action = 'New' if created else 'Updated'
    message = f"{action} after-sales handoff for ticket #{case.service_ticket_id}: {case.summary}"

    for recipient in recipients:
        Notification.objects.create(
            user=recipient,
            ticket=case.service_ticket,
            request=case.service_ticket.request,
            message=message,
            type='info',
        )


def sync_completion_follow_up_case(ticket, reference_date=None):
    if ticket.status != 'Completed':
        return None

    try:
        inspection = ticket.inspection
    except InspectionChecklist.DoesNotExist:
        return None

    if not inspection.follow_up_required:
        return None

    reference_date = reference_date or timezone.localdate()
    case_type = inspection.follow_up_case_type or 'follow_up'
    if case_type == 'maintenance':
        return None

    if case_type == 'warranty' and ticket.warranty_status != 'active':
        case_type = 'follow_up'

    due_date = inspection.follow_up_due_date or _default_completion_follow_up_due_date(
        ticket,
        case_type,
        reference_date,
    )
    priority = 'urgent' if case_type in {'complaint', 'revisit'} else 'high' if case_type == 'warranty' else 'normal'
    requires_revisit = case_type == 'revisit'

    defaults = {
        'client': ticket.request.client,
        'created_by': ticket.technician,
        'priority': priority,
        'summary': inspection.follow_up_summary or _build_completion_follow_up_summary(ticket, case_type),
        'details': _build_completion_follow_up_details(ticket, inspection, case_type),
        'due_date': due_date,
        'requires_revisit': requires_revisit,
        'creation_source': 'completion_flow',
    }

    existing_case = FollowUpCase.objects.filter(
        service_ticket=ticket,
        case_type=case_type,
        creation_source='completion_flow',
    ).exclude(status__in=['resolved', 'closed']).first()

    if existing_case:
        for field, value in defaults.items():
            setattr(existing_case, field, value)
        existing_case.save(update_fields=[*defaults.keys(), 'updated_at'])
        _notify_completion_follow_up_case(existing_case, created=False)
        return existing_case

    case = FollowUpCase.objects.create(
        service_ticket=ticket,
        case_type=case_type,
        status='open',
        assigned_to=None,
        **defaults,
    )
    _notify_completion_follow_up_case(case, created=True)
    return case


def ensure_maintenance_follow_up_case(schedule):
    case = FollowUpCase.objects.filter(
        service_ticket=schedule.service_ticket,
        case_type='maintenance',
        status__in=['open', 'in_progress'],
    ).first()

    rule = get_maintenance_rule(schedule.maintenance_profile)
    summary = f"Scheduled maintenance is approaching for {schedule.client.username}"
    details = (
        f"{rule['label']} maintenance plan. "
        f"Last service date: {schedule.last_service_date}. "
        f"Next due date: {schedule.next_due_date}. "
        f"Interval: {schedule.interval_days} days."
    )
    priority = 'high' if schedule.status == 'due' else 'normal'

    if case:
        case.summary = summary
        case.details = details
        case.priority = priority
        case.due_date = schedule.next_due_date
        case.creation_source = 'maintenance_alert'
        case.save(update_fields=['summary', 'details', 'priority', 'due_date', 'creation_source', 'updated_at'])
        return case

    return FollowUpCase.objects.create(
        service_ticket=schedule.service_ticket,
        client=schedule.client,
        created_by=None,
        case_type='maintenance',
        status='open',
        priority=priority,
        creation_source='maintenance_alert',
        summary=summary,
        details=details,
        due_date=schedule.next_due_date,
    )


def _notify_recipients(schedule, stage):
    User = get_user_model()
    recipients = User.objects.filter(role__in=['superadmin', 'admin', 'follow_up']).distinct()
    stage_label = 'due now' if stage == 'due' else 'coming due'
    title = 'Maintenance alert'
    message = (
        f"{schedule.client.username} is {stage_label} for scheduled maintenance on "
        f"{schedule.next_due_date} ({schedule.get_maintenance_profile_display()})."
    )

    for user in recipients:
        Notification.objects.create(
            user=user,
            ticket=schedule.service_ticket,
            request=schedule.service_ticket.request,
            title=title,
            message=message,
            type='reminder',
        )


def process_maintenance_alerts(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    now = timezone.now()
    summary = {'due_soon': 0, 'due': 0}

    schedules = MaintenanceSchedule.objects.select_related(
        'service_ticket__request',
        'client',
        'service_type',
    ).exclude(status__in=['completed', 'dismissed'])

    for schedule in schedules:
        schedule.status = evaluate_schedule_status(schedule, reference_date=reference_date)
        stage = None

        if schedule.status == 'due' and schedule.due_notified_at is None:
            stage = 'due'
            schedule.due_notified_at = now
        elif schedule.status == 'due_soon' and schedule.due_soon_notified_at is None:
            stage = 'due_soon'
            schedule.due_soon_notified_at = now

        schedule.save()

        if stage:
            ensure_maintenance_follow_up_case(schedule)
            _notify_recipients(schedule, stage)
            summary[stage] += 1

    return summary
