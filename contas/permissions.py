from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def dono_required(view):
    """Exige login e perfil 'dono'. A checagem é feita no servidor a cada requisição."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.eh_dono:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper
