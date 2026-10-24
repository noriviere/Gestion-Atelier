from functools import wraps

from django.core.exceptions import PermissionDenied

from . import roles


def modification_requise(vue):
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not roles.peut_modifier(request.user):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe


def mouvement_requis(vue):
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not roles.peut_mouvementer(request.user):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe
