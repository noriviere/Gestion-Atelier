"""Reprise unique de l'historique de l'ancien classeur « Rapport de production » (onglet Datas)."""
from django.core.management.base import BaseCommand, CommandError

from production.excel import FEUILLE_HISTORIQUE, FichierIllisible, importer_historique

NOMBRE_LIGNES_IGNOREES_AFFICHEES = 20


class Command(BaseCommand):
    help = ("Importe les arrêts de l'ancien classeur Excel du rapport de production. "
            "Relancer l'import sur le même fichier ne crée pas de doublons.")

    def add_arguments(self, parser):
        parser.add_argument("fichier", help="Classeur .xlsx (copie de l'ancien rapport de production).")
        parser.add_argument("--feuille", default=FEUILLE_HISTORIQUE, help=f"Onglet à lire ({FEUILLE_HISTORIQUE} par défaut).")

    def handle(self, *args, **options):
        try:
            with open(options["fichier"], "rb") as fichier:
                bilan = importer_historique(fichier, options["feuille"])
        except (OSError, FichierIllisible) as erreur:
            raise CommandError(str(erreur)) from erreur
        self.stdout.write(self.style.SUCCESS(
            f"{bilan.arrets_crees} arrêts importés dans {bilan.shifts_crees} nouveaux shifts, "
            f"{bilan.doublons} déjà présents."))
        if bilan.causes_creees:
            self.stdout.write(f"Causes ajoutées à la liste : {', '.join(bilan.causes_creees)}.")
        if bilan.equipes_creees:
            self.stdout.write(f"Équipes ajoutées : {', '.join(bilan.equipes_creees)}.")
        if bilan.ignorees:
            self.stdout.write(self.style.WARNING(f"{len(bilan.ignorees)} lignes ignorées :"))
            for numero, raison in bilan.ignorees[:NOMBRE_LIGNES_IGNOREES_AFFICHEES]:
                self.stdout.write(f"  ligne {numero} : {raison}")
            if len(bilan.ignorees) > NOMBRE_LIGNES_IGNOREES_AFFICHEES:
                self.stdout.write(f"  … et {len(bilan.ignorees) - NOMBRE_LIGNES_IGNOREES_AFFICHEES} autres.")
