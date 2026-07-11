from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles):
    """
    Restringe el acceso a una vista según el rol del usuario autenticado.
    Uso: @rol_requerido('administrador', 'empresa')
    """
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if request.user.rol not in roles:
                raise PermissionDenied("No tienes permiso para acceder a este módulo.")
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador
