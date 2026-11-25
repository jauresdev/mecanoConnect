from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import User


class IsShopOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return (
            request.user.is_authenticated
            and (request.user.is_staff or obj.owner_id == request.user.id)
        )


class IsMechanic(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.MECHANIC
        )
