from rest_framework import permissions

from .rbac import (
    AFTER_SALES_MANAGE_CAPABILITIES,
    AFTER_SALES_VIEW_CAPABILITIES,
    MANAGE_STAFF_CAPABILITIES,
    SUPERVISOR_DASHBOARD_CAPABILITIES,
    SUPERVISOR_DISPATCH_CAPABILITIES,
    SUPERVISOR_TICKETS_VIEW,
    SUPERVISOR_TECHNICIAN_DIRECTORY_CAPABILITIES,
    SUPERVISOR_TICKET_CAPABILITIES,
    SUPERVISOR_TRACKING_CAPABILITIES,
    TECHNICIAN_CHECKLIST_CAPABILITIES,
    TECHNICIAN_DASHBOARD_CAPABILITIES,
    TECHNICIAN_HISTORY_CAPABILITIES,
    TECHNICIAN_JOB_DETAIL_CAPABILITIES,
    TECHNICIAN_JOBS_CAPABILITIES,
    TECHNICIAN_NAVIGATION_CAPABILITIES,
    TECHNICIAN_PROFILE_CAPABILITIES,
    TECHNICIAN_SCHEDULE_CAPABILITIES,
    USER_DIRECTORY_VIEW_CAPABILITIES,
    is_admin_workspace_role,
    is_superadmin_role,
    user_has_any_capability,
    user_has_capability,
)


class IsSuperadmin(permissions.BasePermission):
    """Only the owner/superadmin can access."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_superadmin_role(request.user.role)


class IsAdmin(permissions.BasePermission):
    """Superadmins and admins can access the admin workspace."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_admin_workspace_role(request.user.role)


class IsFollowUp(permissions.BasePermission):
    """Only service follow-up users can access."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'follow_up'


class IsSupervisor(permissions.BasePermission):
    """Only supervisor users can access"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'supervisor'


class IsTechnician(permissions.BasePermission):
    """Only technician users can access"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'technician'


class IsClient(permissions.BasePermission):
    """Only client users can access"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'client'


class IsAdminOrSupervisor(permissions.BasePermission):
    """Admin or supervisor can access"""
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and
                (is_admin_workspace_role(request.user.role) or request.user.role == 'supervisor'))


class IsSuperadminOrSupervisor(permissions.BasePermission):
    """Superadmin or supervisor can access."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (is_superadmin_role(request.user.role) or request.user.role == 'supervisor')
        )


class IsAdminOrFollowUp(permissions.BasePermission):
    """Admin or service follow-up users can access."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (is_admin_workspace_role(request.user.role) or request.user.role == 'follow_up')
        )


class IsAdminOrSupervisorOrTechnician(permissions.BasePermission):
    """Admin, supervisor, or technician can access"""
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and
                (is_admin_workspace_role(request.user.role) or request.user.role in ['supervisor', 'technician']))


class IsOwnerOrAdmin(permissions.BasePermission):
    """Object owner or admin can access"""
    def has_object_permission(self, request, view, obj):
        return (request.user and
                (is_admin_workspace_role(request.user.role) or obj.user == request.user))


class CanViewService(permissions.BasePermission):
    """Users can view services based on their role"""
    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin_workspace_role(user.role):
            return True
        elif user.role == 'supervisor':
            return True
        elif user.role == 'technician':
            return obj.technician == user
        elif user.role == 'client':
            return obj.client == user
        return False


class CanManageInventory(permissions.BasePermission):
    """Inventory management permissions"""
    def has_permission(self, request, view):
        user = request.user
        if request.method in permissions.SAFE_METHODS:
            # Read operations allowed for admin, supervisor, technician
            return user and user.is_authenticated and (is_admin_workspace_role(user.role) or user.role in ['supervisor', 'technician'])
        else:
            # Write operations only for admin and supervisor
            return user and user.is_authenticated and (is_admin_workspace_role(user.role) or user.role == 'supervisor')


class CanViewNotifications(permissions.BasePermission):
    """Notification viewing permissions"""
    def has_object_permission(self, request, view, obj):
        return request.user and obj.user == request.user


class CanManageUsers(permissions.BasePermission):
    """Only the superadmin can manage internal account access."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_superadmin_role(request.user.role)


class CanManageStaffCapabilities(permissions.BasePermission):
    """Admins and approved managers can grant staff capabilities."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                is_superadmin_role(request.user.role) or
                user_has_capability(request.user, MANAGE_STAFF_CAPABILITIES)
            )
        )


class CanViewUserDirectory(permissions.BasePermission):
    """Allow superadmins, approved admins, and delegated supervisors to view user lists."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                is_superadmin_role(request.user.role) or
                (
                    request.user.role == 'admin' and
                    user_has_any_capability(request.user, USER_DIRECTORY_VIEW_CAPABILITIES)
                ) or
                user_has_capability(request.user, MANAGE_STAFF_CAPABILITIES)
            )
        )


class CanManageServiceRequests(permissions.BasePermission):
    """Admins or supervisors with ticket-queue access can manage requests."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                is_admin_workspace_role(request.user.role) or
                (
                    request.user.role == 'supervisor' and
                    user_has_capability(request.user, SUPERVISOR_TICKETS_VIEW)
                )
            )
        )


class RoleCapabilityPermission(permissions.BasePermission):
    required_role = None
    capability_codes = set()

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == self.required_role and
            user_has_any_capability(request.user, self.capability_codes)
        )


class AdminOrRoleCapabilityPermission(RoleCapabilityPermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                is_admin_workspace_role(request.user.role) or
                super().has_permission(request, view)
            )
        )


class CanAccessAfterSales(AdminOrRoleCapabilityPermission):
    """Follow-up users can open after-sales pages when granted."""

    required_role = 'follow_up'
    capability_codes = AFTER_SALES_VIEW_CAPABILITIES


class CanManageAfterSalesCases(AdminOrRoleCapabilityPermission):
    """Follow-up users can create and update after-sales cases when granted."""

    required_role = 'follow_up'
    capability_codes = AFTER_SALES_MANAGE_CAPABILITIES


class CanViewSupervisorDashboard(RoleCapabilityPermission):
    required_role = 'supervisor'
    capability_codes = SUPERVISOR_DASHBOARD_CAPABILITIES


class CanViewSupervisorTickets(AdminOrRoleCapabilityPermission):
    required_role = 'supervisor'
    capability_codes = SUPERVISOR_TICKET_CAPABILITIES


class CanViewSupervisorDispatch(AdminOrRoleCapabilityPermission):
    required_role = 'supervisor'
    capability_codes = SUPERVISOR_DISPATCH_CAPABILITIES


class CanViewSupervisorTracking(AdminOrRoleCapabilityPermission):
    required_role = 'supervisor'
    capability_codes = SUPERVISOR_TRACKING_CAPABILITIES


class CanViewSupervisorTechnicianDirectory(AdminOrRoleCapabilityPermission):
    required_role = 'supervisor'
    capability_codes = SUPERVISOR_TECHNICIAN_DIRECTORY_CAPABILITIES


class CanViewTechnicianDashboard(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_DASHBOARD_CAPABILITIES


class CanViewTechnicianJobs(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_JOBS_CAPABILITIES


class CanViewTechnicianJobDetails(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_JOB_DETAIL_CAPABILITIES


class CanViewTechnicianSchedule(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_SCHEDULE_CAPABILITIES


class CanViewTechnicianNavigation(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_NAVIGATION_CAPABILITIES


class CanViewTechnicianChecklist(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_CHECKLIST_CAPABILITIES


class CanViewTechnicianHistory(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_HISTORY_CAPABILITIES


class CanViewTechnicianProfile(RoleCapabilityPermission):
    required_role = 'technician'
    capability_codes = TECHNICIAN_PROFILE_CAPABILITIES
