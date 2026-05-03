from collections import OrderedDict

SUPERADMIN_ROLE = 'superadmin'
ADMIN_ROLE = 'admin'
ADMIN_WORKSPACE_ROLES = {SUPERADMIN_ROLE, ADMIN_ROLE}
ADMIN_SCOPED_ROLES = ADMIN_WORKSPACE_ROLES | {'follow_up'}
ADMIN_SCOPE_DEFAULTS = {
    SUPERADMIN_ROLE: 'general',
    ADMIN_ROLE: 'general',
    'follow_up': 'service_follow_up',
}
DELEGATED_AUTHORITY_ROLES = {'technician', 'follow_up'}

AFTER_SALES_DASHBOARD_VIEW = 'after_sales.dashboard.view'
AFTER_SALES_CASES_VIEW = 'after_sales.cases.view'
AFTER_SALES_CASES_MANAGE = 'after_sales.cases.manage'
SUPERVISOR_DASHBOARD_VIEW = 'supervisor.dashboard.view'
SUPERVISOR_TICKETS_VIEW = 'supervisor.tickets.view'
SUPERVISOR_DISPATCH_VIEW = 'supervisor.dispatch.view'
SUPERVISOR_TRACKING_VIEW = 'supervisor.tracking.view'
TECHNICIAN_DASHBOARD_VIEW = 'technician.dashboard.view'
TECHNICIAN_JOBS_VIEW = 'technician.jobs.view'
TECHNICIAN_SCHEDULE_VIEW = 'technician.schedule.view'
TECHNICIAN_NAVIGATION_VIEW = 'technician.navigation.view'
TECHNICIAN_CHECKLIST_VIEW = 'technician.checklist.view'
TECHNICIAN_MESSAGES_VIEW = 'technician.messages.view'
TECHNICIAN_HISTORY_VIEW = 'technician.history.view'
TECHNICIAN_PROFILE_VIEW = 'technician.profile.view'
ADMIN_JOB_HISTORY_VIEW = 'admin.job_history.view'
MANAGE_STAFF_CAPABILITIES = 'users.capabilities.manage_staff'
USER_DIRECTORY_VIEW = 'users.directory.view'


CAPABILITY_DEFINITIONS = OrderedDict([
    (
        AFTER_SALES_DASHBOARD_VIEW,
        {
            'label': 'View after-sales dashboard',
            'description': 'Open the after-sales dashboard and review case health.',
            'category': 'After Sales',
            'assignable': True,
        },
    ),
    (
        AFTER_SALES_CASES_VIEW,
        {
            'label': 'View after-sales cases',
            'description': 'Open the after-sales queue and review customer recovery cases.',
            'category': 'After Sales',
            'assignable': True,
        },
    ),
    (
        AFTER_SALES_CASES_MANAGE,
        {
            'label': 'Manage after-sales cases',
            'description': 'Create and update after-sales cases for completed tickets.',
            'category': 'After Sales',
            'assignable': True,
        },
    ),
    (
        SUPERVISOR_DASHBOARD_VIEW,
        {
            'label': 'Open supervisor dashboard',
            'description': 'View the supervisor dashboard and queue health.',
            'category': 'Supervisor',
            'assignable': True,
        },
    ),
    (
        SUPERVISOR_TICKETS_VIEW,
        {
            'label': 'Open supervisor tickets',
            'description': 'Review service tickets inside the supervisor workspace.',
            'category': 'Supervisor',
            'assignable': True,
        },
    ),
    (
        SUPERVISOR_DISPATCH_VIEW,
        {
            'label': 'Open dispatch board',
            'description': 'Assign technicians and manage dispatch decisions.',
            'category': 'Supervisor',
            'assignable': True,
        },
    ),
    (
        SUPERVISOR_TRACKING_VIEW,
        {
            'label': 'Open technician tracking',
            'description': 'Monitor technician locations and live movement.',
            'category': 'Supervisor',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_DASHBOARD_VIEW,
        {
            'label': 'Open technician dashboard',
            'description': 'View the technician dashboard and daily workload.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_JOBS_VIEW,
        {
            'label': 'Open technician jobs',
            'description': 'Open the My Jobs page and update assigned work.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_SCHEDULE_VIEW,
        {
            'label': 'Open technician schedule',
            'description': 'Review the technician schedule and upcoming appointments.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_NAVIGATION_VIEW,
        {
            'label': 'Open technician navigation',
            'description': 'Open route guidance for assigned technician jobs.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_CHECKLIST_VIEW,
        {
            'label': 'Open technician checklist',
            'description': 'Use the technician checklist and proof-of-work flow.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_MESSAGES_VIEW,
        {
            'label': 'Open technician messages',
            'description': 'Open the technician messaging view.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_HISTORY_VIEW,
        {
            'label': 'Open technician history',
            'description': 'Review completed technician jobs and recent history.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        TECHNICIAN_PROFILE_VIEW,
        {
            'label': 'Open technician profile',
            'description': 'Open and update the technician profile page.',
            'category': 'Technician',
            'assignable': True,
        },
    ),
    (
        MANAGE_STAFF_CAPABILITIES,
        {
            'label': 'Manage staff capabilities',
            'description': 'Grant and revoke approved staff capabilities.',
            'category': 'Supervisor',
            'assignable': True,
        },
    ),
    (
        USER_DIRECTORY_VIEW,
        {
            'label': 'View user directory',
            'description': 'Open the user directory and review internal and client accounts.',
            'category': 'Administration',
            'assignable': True,
        },
    ),
    (
        ADMIN_JOB_HISTORY_VIEW,
        {
            'label': 'View job history & heatmap',
            'description': 'Open the completed job history page and service location heatmap.',
            'category': 'Administration',
            'assignable': True,
        },
    ),
])


STAFF_ROLE_CAPABILITY_MAP = {
    'follow_up': {
        AFTER_SALES_DASHBOARD_VIEW,
        AFTER_SALES_CASES_VIEW,
        AFTER_SALES_CASES_MANAGE,
    },
    'supervisor': {
        SUPERVISOR_DASHBOARD_VIEW,
        SUPERVISOR_TICKETS_VIEW,
        SUPERVISOR_DISPATCH_VIEW,
        SUPERVISOR_TRACKING_VIEW,
        MANAGE_STAFF_CAPABILITIES,
    },
    'technician': {
        TECHNICIAN_DASHBOARD_VIEW,
        TECHNICIAN_JOBS_VIEW,
        TECHNICIAN_SCHEDULE_VIEW,
        TECHNICIAN_NAVIGATION_VIEW,
        TECHNICIAN_CHECKLIST_VIEW,
        TECHNICIAN_MESSAGES_VIEW,
        TECHNICIAN_HISTORY_VIEW,
        TECHNICIAN_PROFILE_VIEW,
    },
}

STAFF_ROLES = set(STAFF_ROLE_CAPABILITY_MAP.keys())

MANAGEABLE_STAFF_ROLES = STAFF_ROLES

AFTER_SALES_VIEW_CAPABILITIES = {
    AFTER_SALES_DASHBOARD_VIEW,
    AFTER_SALES_CASES_VIEW,
    AFTER_SALES_CASES_MANAGE,
}

AFTER_SALES_MANAGE_CAPABILITIES = {
    AFTER_SALES_CASES_MANAGE,
}

SUPERVISOR_DASHBOARD_CAPABILITIES = {
    SUPERVISOR_DASHBOARD_VIEW,
}

SUPERVISOR_TICKET_CAPABILITIES = {
    SUPERVISOR_TICKETS_VIEW,
    SUPERVISOR_DISPATCH_VIEW,
    SUPERVISOR_TRACKING_VIEW,
}

SUPERVISOR_DISPATCH_CAPABILITIES = {
    SUPERVISOR_DISPATCH_VIEW,
}

SUPERVISOR_TRACKING_CAPABILITIES = {
    SUPERVISOR_TRACKING_VIEW,
}

SUPERVISOR_TECHNICIAN_DIRECTORY_CAPABILITIES = {
    SUPERVISOR_DISPATCH_VIEW,
    SUPERVISOR_TRACKING_VIEW,
}

TECHNICIAN_DASHBOARD_CAPABILITIES = {
    TECHNICIAN_DASHBOARD_VIEW,
}

TECHNICIAN_JOBS_CAPABILITIES = {
    TECHNICIAN_JOBS_VIEW,
}

TECHNICIAN_JOB_DETAIL_CAPABILITIES = {
    TECHNICIAN_JOBS_VIEW,
    TECHNICIAN_NAVIGATION_VIEW,
    TECHNICIAN_CHECKLIST_VIEW,
}

TECHNICIAN_SCHEDULE_CAPABILITIES = {
    TECHNICIAN_SCHEDULE_VIEW,
}

TECHNICIAN_NAVIGATION_CAPABILITIES = {
    TECHNICIAN_NAVIGATION_VIEW,
}

TECHNICIAN_CHECKLIST_CAPABILITIES = {
    TECHNICIAN_CHECKLIST_VIEW,
}

TECHNICIAN_MESSAGES_CAPABILITIES = {
    TECHNICIAN_MESSAGES_VIEW,
}

TECHNICIAN_HISTORY_CAPABILITIES = {
    TECHNICIAN_HISTORY_VIEW,
}

TECHNICIAN_PROFILE_CAPABILITIES = {
    TECHNICIAN_PROFILE_VIEW,
}

USER_DIRECTORY_VIEW_CAPABILITIES = {
    USER_DIRECTORY_VIEW,
}

ADMIN_JOB_HISTORY_CAPABILITIES = {
    ADMIN_JOB_HISTORY_VIEW,
}


ROLE_CAPABILITY_MAP = {
    SUPERADMIN_ROLE: set(CAPABILITY_DEFINITIONS.keys()),
    ADMIN_ROLE: {
        code for code in CAPABILITY_DEFINITIONS.keys()
        if code not in {MANAGE_STAFF_CAPABILITIES, USER_DIRECTORY_VIEW, ADMIN_JOB_HISTORY_VIEW}
    },
    'follow_up': set(STAFF_ROLE_CAPABILITY_MAP['follow_up']),
    'supervisor': set(STAFF_ROLE_CAPABILITY_MAP['supervisor']),
    'technician': set(STAFF_ROLE_CAPABILITY_MAP['technician']),
    'client': set(),
}


def get_role_capabilities(role):
    return set(ROLE_CAPABILITY_MAP.get(role or '', set()))


def get_capability_catalog(*, include_non_assignable=False):
    catalog = []
    for code, metadata in CAPABILITY_DEFINITIONS.items():
        if not include_non_assignable and not metadata.get('assignable', False):
            continue
        catalog.append({
            'code': code,
            **metadata,
        })
    return catalog


def get_staff_role_capability_codes(role):
    return set(STAFF_ROLE_CAPABILITY_MAP.get(role or '', set()))


def is_superadmin_role(role):
    return (role or '') == SUPERADMIN_ROLE


def is_admin_workspace_role(role):
    return (role or '') in ADMIN_WORKSPACE_ROLES


def is_admin_scoped_role(role):
    return (role or '') in ADMIN_SCOPED_ROLES


def get_default_admin_scope_for_role(role):
    return ADMIN_SCOPE_DEFAULTS.get(role or '')


def can_receive_delegated_authority(role):
    return (role or '') in DELEGATED_AUTHORITY_ROLES


def is_staff_role(role):
    return (role or '') in STAFF_ROLES


def get_assignable_capability_codes(actor, target_user=None):
    if not actor or not getattr(actor, 'is_authenticated', False):
        return set()

    target_role = getattr(target_user, 'role', None)

    if is_superadmin_role(getattr(actor, 'role', None)):
        if target_role and is_staff_role(target_role):
            return get_staff_role_capability_codes(target_role)
        return {
            item['code']
            for item in get_capability_catalog(include_non_assignable=False)
        }

    if user_has_capability(actor, MANAGE_STAFF_CAPABILITIES):
        if target_role and can_receive_delegated_authority(target_role):
            return get_staff_role_capability_codes(target_role)
        return set(AFTER_SALES_VIEW_CAPABILITIES)

    return set()


def normalize_capability_codes(capability_codes):
    normalized_codes = []
    for code in capability_codes or []:
        normalized_code = str(code or '').strip()
        if normalized_code and normalized_code not in normalized_codes:
            normalized_codes.append(normalized_code)
    return normalized_codes


def get_unknown_capability_codes(capability_codes):
    known_codes = set(CAPABILITY_DEFINITIONS.keys())
    return sorted(set(normalize_capability_codes(capability_codes)) - known_codes)


def get_user_direct_capability_codes(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return set()

    prefetched_grants = getattr(user, '_prefetched_objects_cache', {}).get('capability_grants')
    if prefetched_grants is not None:
        return {grant.capability_code for grant in prefetched_grants}

    return set(user.capability_grants.values_list('capability_code', flat=True))


def get_user_capability_codes(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return set()

    role = getattr(user, 'role', None)
    role_capabilities = get_role_capabilities(role)
    direct_capabilities = get_user_direct_capability_codes(user)

    if role in STAFF_ROLES and direct_capabilities:
        return direct_capabilities

    return role_capabilities | direct_capabilities


def user_has_capability(user, capability_code):
    return capability_code in get_user_capability_codes(user)


def user_has_any_capability(user, capability_codes):
    effective_capabilities = get_user_capability_codes(user)
    return bool(effective_capabilities.intersection(set(capability_codes or [])))


def user_has_role_capability(user, role, capability_code):
    return getattr(user, 'role', None) == role and user_has_capability(user, capability_code)


def user_has_any_role_capability(user, role, capability_codes):
    return getattr(user, 'role', None) == role and user_has_any_capability(user, capability_codes)


def can_manage_user_capabilities(actor, target_user):
    if not actor or not getattr(actor, 'is_authenticated', False):
        return False

    target_role = getattr(target_user, 'role', None) if target_user else None

    if is_superadmin_role(getattr(actor, 'role', None)):
        if target_user is None:
            return True
        return target_role in (MANAGEABLE_STAFF_ROLES | {ADMIN_ROLE})

    if not user_has_capability(actor, MANAGE_STAFF_CAPABILITIES):
        return False

    if not target_user:
        return True

    if target_user.id == actor.id:
        return False

    return can_receive_delegated_authority(target_role)
