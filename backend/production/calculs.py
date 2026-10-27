"""Calculs du rapport de production : créneaux, temps de marche, quantités et rendement.

Il n'y a pas de TRS : le rendement compare la quantité produite à ce que la cadence
de la fiche produit-machine permettait pendant le temps de marche.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone

MINUTES_PAR_HEURE = Decimal(60)


def bornes_du_creneau(jour, heure_debut, heure_fin):
    """Début et fin (heure locale) d'un créneau qui commence le jour donné ; la nuit finit le lendemain."""
    debut = timezone.make_aware(datetime.combine(jour, heure_debut))
    fin = timezone.make_aware(datetime.combine(jour, heure_fin))
    if fin <= debut:
        fin = timezone.make_aware(datetime.combine(jour + timedelta(days=1), heure_fin))
    return debut, fin


def duree_en_minutes(debut, fin):
    return max(0, int((fin - debut).total_seconds() // 60))


def creneau_a_l_heure(moment, creneaux):
    """(jour, créneau) en cours au moment donné, ou (None, None) entre deux créneaux.

    Le jour est celui où le créneau commence : à 2 h du matin, c'est la nuit de la veille.
    """
    moment = timezone.localtime(moment)
    for jour in (moment.date(), moment.date() - timedelta(days=1)):
        for creneau in creneaux:
            if creneau.travaille_le(jour):
                debut, fin = creneau.bornes(jour)
                if debut <= moment < fin:
                    return jour, creneau
    return None, None


def quantite(compteur_debut, compteur_fin):
    """Compteur remis à zéro : la valeur de fin ; sinon, fin moins début."""
    if compteur_fin is None:
        return None
    return compteur_fin - (compteur_debut or 0)


def quantite_attendue(cadence, temps_de_marche):
    """Pièces que la cadence (pièces/heure) permettait pendant le temps de marche (minutes)."""
    if not cadence:
        return None
    return Decimal(cadence) * temps_de_marche / MINUTES_PAR_HEURE


def rendement(quantite_produite, attendue):
    """Rapport entre 0 et plus de 1, ou None quand il ne peut pas être calculé."""
    if quantite_produite is None or not attendue:
        return None
    return Decimal(quantite_produite) / Decimal(attendue)


@dataclass
class BilanTroncon:
    """Une partie du shift passée sur un même produit."""

    troncon: object
    fin: datetime
    duree: int
    arrets: int
    marche: int
    quantite: int | None
    attendue: Decimal | None
    rendement: Decimal | None


@dataclass
class Bilan:
    """Totaux d'un shift ou d'un ensemble de shifts."""

    theorique: int = 0
    arrets: int = 0
    quantite: int = 0
    # Quantité et attendu des seuls tronçons qui ont une quantité et une cadence : ils font le rendement.
    quantite_comparable: int = 0
    attendue: Decimal = Decimal(0)
    troncons: list = field(default_factory=list)

    @property
    def marche(self):
        return max(0, self.theorique - self.arrets)

    @property
    def rendement(self):
        return rendement(self.quantite_comparable, self.attendue)

    def ajouter(self, autre):
        self.theorique += autre.theorique
        self.arrets += autre.arrets
        self.quantite += autre.quantite
        self.quantite_comparable += autre.quantite_comparable
        self.attendue += autre.attendue
        return self


def bilan_du_shift(shift):
    """Bilan d'un shift à partir de ses tronçons et arrêts (préchargés de préférence).

    Chaque tronçon va de son début au début du suivant, ou à la fin du shift ; ses arrêts
    sont ceux qui lui sont rattachés.
    """
    troncons = sorted(shift.troncons.all(), key=lambda troncon: troncon.debut)
    arrets = list(shift.arrets.all())
    bilan = Bilan(theorique=duree_en_minutes(shift.debut, shift.fin), arrets=sum(arret.duree for arret in arrets))
    for position, troncon in enumerate(troncons):
        fin = troncons[position + 1].debut if position + 1 < len(troncons) else shift.fin
        debut = min(max(troncon.debut, shift.debut), shift.fin)
        duree = duree_en_minutes(debut, min(fin, shift.fin))
        arrets_du_troncon = sum(arret.duree for arret in arrets if arret.troncon_id == troncon.pk)
        marche = max(0, duree - arrets_du_troncon)
        produit = troncon.quantite
        attendue = quantite_attendue(troncon.cadence, marche)
        bilan.troncons.append(BilanTroncon(troncon, fin, duree, arrets_du_troncon, marche, produit, attendue,
                                           rendement(produit, attendue)))
        if produit is not None:
            bilan.quantite += produit
            if attendue:
                bilan.quantite_comparable += produit
                bilan.attendue += attendue
    return bilan
