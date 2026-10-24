from functools import wraps

from django.core.exceptions import PermissionDenied

from . import roles


def droit_requis(code):
    """Refuse la vue (403) à qui n'a pas la sous-fonction `code` du catalogue des droits (comptes/droits.py)."""

    def decorateur(vue):
        @wraps(vue)
        def enveloppe(request, *args, **kwargs):
            if not roles.a_le_droit(request.user, code):
                raise PermissionDenied
            return vue(request, *args, **kwargs)

        return enveloppe

    return decorateur
