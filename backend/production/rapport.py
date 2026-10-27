"""L'écran unique du rapport de production : sélection des shifts, totaux, Pareto des causes et évolution."""
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from .calculs import Bilan
from .models import Shift

# Au-delà, l'évolution se lit par semaine plutôt que par jour.
JOURS_MAXI_PAR_JOUR = 31


def veille():
    return timezone.localdate() - timedelta(days=1)


def periodes_rapides():
    """Raccourcis de période : (libellé, du, au)."""
    hier = veille()
    return [("Veille", hier, hier), ("7 derniers jours", hier - timedelta(days=6), hier),
            ("30 derniers jours", hier - timedelta(days=29), hier)]


def selectionner_shifts(du, au, machine=None, equipe=None, creneau=None, produit=None, cause=None):
    shifts = (Shift.objects.filter(jour__range=(du, au))
              .select_related("machine", "creneau", "equipe", "matricule")
              .prefetch_related("troncons__produit", "arrets__cause"))
    if machine:
        shifts = shifts.filter(machine=machine)
    if equipe:
        shifts = shifts.filter(equipe=equipe)
    if creneau:
        shifts = shifts.filter(creneau=creneau)
    if produit:
        shifts = shifts.filter(troncons__produit=produit)
    if cause:
        shifts = shifts.filter(arrets__cause=cause)
    return shifts.distinct().order_by("jour", "creneau__ordre", "machine__code")


@dataclass
class LignePareto:
    cause: object
    minutes: int
    nombre: int
    part: float
    cumul: float
    largeur: float


@dataclass
class PointEvolution:
    libelle: str
    quantite: int
    arrets: int
    rendement: object
    largeur: float


def pareto(shifts):
    """Causes d'arrêt de la plus longue à la plus courte, avec leur part du temps d'arrêt et le cumul."""
    minutes, nombres = defaultdict(int), defaultdict(int)
    for shift in shifts:
        for arret in shift.arrets.all():
            minutes[arret.cause] += arret.duree
            nombres[arret.cause] += 1
    total = sum(minutes.values())
    lignes, cumul = [], 0
    plus_longue = max(minutes.values(), default=0)
    for cause, duree in sorted(minutes.items(), key=lambda element: (-element[1], element[0].libelle)):
        cumul += duree
        lignes.append(LignePareto(cause, duree, nombres[cause], 100 * duree / total, 100 * cumul / total,
                                  100 * duree / plus_longue))
    return lignes


def evolution(shifts, du, au):
    """Quantité, arrêts et rendement par jour (ou par semaine sur une longue période).

    La barre suit la quantité, rapportée à la plus grande de la période.
    """
    par_semaine = (au - du).days >= JOURS_MAXI_PAR_JOUR
    groupes = OrderedDict()
    for shift in sorted(shifts, key=lambda shift: shift.jour):
        if par_semaine:
            lundi = shift.jour - timedelta(days=shift.jour.weekday())
            cle, libelle = lundi, f"Sem. {lundi.isocalendar()[1]} ({lundi:%d/%m})"
        else:
            cle, libelle = shift.jour, f"{shift.jour:%d/%m}"
        groupes.setdefault(cle, (libelle, Bilan()))[1].ajouter(shift.bilan())
    plus_grande = max((bilan.quantite for _, bilan in groupes.values()), default=0)
    points = []
    for libelle, bilan in groupes.values():
        largeur = 100 * bilan.quantite / plus_grande if plus_grande else 0
        points.append(PointEvolution(libelle, bilan.quantite, bilan.arrets, bilan.rendement, largeur))
    return points, par_semaine


def construire_rapport(shifts, du, au):
    shifts = list(shifts)
    total = Bilan()
    for shift in shifts:
        total.ajouter(shift.bilan())
    points, par_semaine = evolution(shifts, du, au)
    return {"shifts": shifts, "total": total, "pareto": pareto(shifts), "evolution": points,
            "evolution_par_semaine": par_semaine}
