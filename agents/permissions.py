from rest_framework.permissions import BasePermission


class IsCFOOrAdmin(BasePermission):

    def has_permission(self, request, view):

        user = request.user

        if not user.is_authenticated:
            return False

        return (
            user.groups.filter(name="CFO").exists()
            or user.groups.filter(name="Admin").exists()
        )

class IsFinanceManagerOrAdmin(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated and (
                request.user.groups.filter(name="Finance Manager").exists()
                or request.user.groups.filter(name="Admin").exists()
            )
        )


class IsAuditorOrAdmin(BasePermission):

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated and (
                request.user.groups.filter(name="Auditor").exists()
                or request.user.groups.filter(name="Admin").exists()
            )
        )


