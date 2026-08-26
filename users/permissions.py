from rest_framework import permissions

class IsNotBlockedOrSuspended(permissions.BasePermission):
    """
    Permission class checking if the user is authenticated and neither blocked nor suspended.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if getattr(request.user, 'is_blocked', False):
            return False
        if getattr(request.user, 'is_currently_suspended', lambda: False)():
            return False
        return True


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allows safe methods to anyone, and write methods only to the object author/owner or admin.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check admin
        if request.user.is_staff or getattr(request.user, 'is_hostel_admin', False):
            return True
        
        # Check author/user attribute
        owner = getattr(obj, 'author', getattr(obj, 'user', getattr(obj, 'uploader', None)))
        return owner == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read access to all authenticated/unauthenticated, and write access only to staff/admin.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'is_hostel_admin', False))


class IsChiefAdmin(permissions.BasePermission):
    """
    Allows access only to Chief Admins (superusers/staff).
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff and not request.user.is_blocked)


class IsChiefAdminOrReadOnly(permissions.BasePermission):
    """
    Allows read access (GET, HEAD, OPTIONS) to all users (students, visitors),
    and write access (POST, PUT, PATCH, DELETE) ONLY to Chief Admin / Staff (is_staff=True, is_active=True, not is_blocked).
    Students, Wardens (is_hostel_admin without is_staff), and non-admin users are strictly denied write access.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff and
            request.user.is_active and
            not getattr(request.user, 'is_blocked', False)
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff and
            request.user.is_active and
            not getattr(request.user, 'is_blocked', False)
        )



