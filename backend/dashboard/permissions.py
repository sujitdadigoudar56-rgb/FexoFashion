from rest_framework import permissions


class IsStaff(permissions.BasePermission):
    """Only active staff users can use the /api/admin/ endpoints."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)
