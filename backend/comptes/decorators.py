from functools import wraps

from django.core.exceptions import PermissionDenied

from . import roles


def documents_autorises(vue):
    """Photos et documents des fiches : Admin, Méthode et management, régleurs."""
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not roles.peut_documenter(request.user):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe


def modification_requise(vue):
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not roles.peut_modifier(request.user):
            raise PermissionDenied
        return vue(request, *args, **kwargs)

    return enveloppe
