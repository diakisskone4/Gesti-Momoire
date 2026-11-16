from rest_framework import permissions

class IsProjectOwnerOrSupervisor(permissions.BasePermission):
    """
    Permission personnalisée pour vérifier que l'utilisateur est le propriétaire du projet
    ou un superviseur.
    """
    
    def has_object_permission(self, request, view, obj):
        # Vérifier si l'utilisateur est le propriétaire
        if hasattr(obj, 'project'):
            # Pour les chapitres, références, etc.
            return obj.project.user == request.user
        elif hasattr(obj, 'user'):
            # Pour les projets
            return obj.user == request.user
        return False
    
    def has_permission(self, request, view):
        # Vérifier que l'utilisateur est authentifié
        return request.user and request.user.is_authenticated


class IsSupervisor(permissions.BasePermission):
    """
    Permission pour vérifier si l'utilisateur est un superviseur.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'SUPERVISOR'

class HasRole(permissions.BasePermission):
    """Autorise uniquement les utilisateurs dont le rôle figure dans `roles`."""
    roles = ()

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in self.roles)


class IsAdminRole(HasRole):
    roles = ('ADMIN',)


class IsReviewerRole(HasRole):
    """Encadreur, co-encadreur ou membre du jury."""
    roles = ('SUPERVISOR', 'CO_SUPERVISOR', 'JURY')
