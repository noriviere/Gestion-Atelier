"""Ménage des fichiers déposés : un fichier sans document qui s'en sert est effacé du disque."""
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Document


@receiver(post_delete, sender=Document)
def effacer_fichier_orphelin(sender, instance, **kwargs):
    """Aussi pour un produit ou une fiche supprimés (en cascade, y compris depuis l'administration).

    Un produit ou une fiche dupliqués partagent le fichier : il n'est effacé qu'au dernier document qui s'en sert,
    une fois la suppression enregistrée en base."""
    nom_fichier, stockage = instance.fichier.name, instance.fichier.storage

    def effacer_si_orphelin():
        if nom_fichier and not Document.objects.filter(fichier=nom_fichier).exists():
            stockage.delete(nom_fichier)

    transaction.on_commit(effacer_si_orphelin)
