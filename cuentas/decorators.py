from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def admin_requerido(vista):
    """Restringe una vista a usuarios administradores (RF-06, RNF-04)."""

    @wraps(vista)
    def _envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not getattr(request.user, 'es_admin', False):
            messages.error(request, 'No tenés permisos para acceder al panel administrativo.')
            return redirect('tienda:inicio')
        return vista(request, *args, **kwargs)

    return _envoltura
