from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission: Only the owner (reporter) can edit/delete the object.
    Read-only allowed for others.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions only for the reporter
        return hasattr(obj, 'reporter') and obj.reporter == request.user


class IsTrustedReporter(permissions.BasePermission):
    """
    Allow only trusted reporters to create or manage certain objects.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'is_trusted_reporter', False)

