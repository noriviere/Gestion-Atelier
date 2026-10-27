from datetime import time

from django.db import migrations

# Listes de départ, modifiables ensuite dans le paramétrage. Écrites ici pour que la migration ne change pas plus tard.
EQUIPES = [("E1", "Matin ou après-midi, en alternance avec E2"), ("E2", "Matin ou après-midi, en alternance avec E1"),
           ("E3", "Nuit"), ("E4", "Weekend")]
CRENEAUX = [
    # nom, début, fin, jours de début (0 lundi … 6 dimanche)
    ("Matin", time(5), time(13), "01234"),
    ("Après-midi", time(13), time(21), "01234"),
    ("Nuit", time(21), time(5), "01234"),
    ("Weekend", time(6), time(18), "56"),
]
# libellé, commentaire obligatoire : causes de l'ancien classeur, puis causes classiques d'atelier.
CAUSES = [
    ("Pause", False), ("Réunion", False), ("Nettoyage", False), ("Organisation", False), ("Outillages", False),
    ("Maintenance préventive", False), ("Changement de série / réglage", False),
    ("Changement de meule ou de bande", False), ("Panne machine", False), ("Attente matière", False),
    ("Attente régleur", False), ("Contrôle qualité", False), ("Manque de personnel", False), ("Essais", False),
    ("Autre", True),
]


def creer_les_listes(apps, schema_editor):
    Equipe = apps.get_model("production", "Equipe")
    Creneau = apps.get_model("production", "Creneau")
    CauseArret = apps.get_model("production", "CauseArret")
    for code, nom in EQUIPES:
        Equipe.objects.get_or_create(code=code, defaults={"nom": nom})
    for ordre, (nom, debut, fin, jours) in enumerate(CRENEAUX):
        Creneau.objects.get_or_create(nom=nom, defaults={"heure_debut": debut, "heure_fin": fin, "jours": jours,
                                                         "ordre": ordre})
    for ordre, (libelle, commentaire_obligatoire) in enumerate(CAUSES):
        CauseArret.objects.get_or_create(libelle=libelle, defaults={
            "commentaire_obligatoire": commentaire_obligatoire, "ordre": ordre})


class Migration(migrations.Migration):
    dependencies = [("production", "0001_initial")]
    operations = [migrations.RunPython(creer_les_listes, migrations.RunPython.noop)]
