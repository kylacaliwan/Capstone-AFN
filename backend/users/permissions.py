from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Only admin users can access"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


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
                request.user.role in ['admin', 'supervisor'])


class IsAdminOrFollowUp(permissions.BasePermission):
    """Admin or service follow-up users can access."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['admin', 'follow_up']
        )


class IsAdminOrSupervisorOrTechnician(permissions.BasePermission):
    """Admin, supervisor, or technician can access"""
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and
                request.user.role in ['admin', 'supervisor', 'technician'])


class IsOwnerOrAdmin(permissions.BasePermission):
    """Object owner or admin can access"""
    def has_object_permission(self, request, view, obj):
        return (request.user and
                (request.user.role == 'admin' or obj.user == request.user))


class CanViewService(permissions.BasePermission):
    """Users can view services based on their role"""
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == 'admin':
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
            return user and user.is_authenticated and user.role in ['admin', 'supervisor', 'technician']
        else:
            # Write operations only for admin and supervisor
            return user and user.is_authenticated and user.role in ['admin', 'supervisor']


class CanViewNotifications(permissions.BasePermission):
    """Notification viewing permissions"""
    def has_object_permission(self, request, view, obj):
        return request.user and obj.user == request.user


class CanManageUsers(permissions.BasePermission):
    """User management permissions"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'
