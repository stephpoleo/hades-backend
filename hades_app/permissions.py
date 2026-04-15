"""
Clases de permisos personalizadas para Hades Backend.

Roles:
    1 = Empleado
    2 = Administrador
    3 = Supervisor
"""

from rest_framework.permissions import BasePermission, IsAuthenticated  # noqa: F401

EMPLOYEE_ROLE = 1
ADMIN_ROLE = 2
SUPERVISOR_ROLE = 3


class IsAdminRole(BasePermission):
    """Solo Administradores (rol 2) y superusers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return getattr(request.user, "id_role_fk", None) == ADMIN_ROLE


class IsAdminOrSupervisor(BasePermission):
    """Administradores (rol 2) y Supervisores (rol 3), y superusers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return getattr(request.user, "id_role_fk", None) in (ADMIN_ROLE, SUPERVISOR_ROLE)


class IsEmployeeOrAdmin(BasePermission):
    """Empleados (rol 1) y Administradores (rol 2), y superusers."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return getattr(request.user, "id_role_fk", None) in (EMPLOYEE_ROLE, ADMIN_ROLE)
