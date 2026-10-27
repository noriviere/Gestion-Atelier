"""Rapport de production : équipes, créneaux, causes d'arrêt et saisies de chaque shift.

Un shift, c'est une machine, une équipe et un créneau d'une date. Il est découpé en tronçons,
un par produit fabriqué, et porte les arrêts saisis au fil du shift.
"""
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from produits.models import Machine, Produit
from remontees.models import Matricule

from . import calculs

JOURS_DE_LA_SEMAINE = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


class Equipe(models.Model):
    code = models.CharField(max_length=10, unique=True, help_text="Par exemple E1.")
    nom = models.CharField(max_length=80, blank=True)
    actif = models.BooleanField(default=True, help_text="Décoché : n'est plus proposée à l'ouverture d'un shift.")

    class Meta:
        ordering = ["code"]
        verbose_name = "équipe"

    def __str__(self):
        return self.code


class Creneau(models.Model):
    """Plage horaire d'un shift. Les équipes E1 et E2 alternent sur les créneaux : l'équipe se choisit à la main."""

    nom = models.CharField(max_length=40, unique=True)
    heure_debut = models.TimeField("heure de début")
    heure_fin = models.TimeField("heure de fin", help_text="Plus tôt que le début : le créneau finit le lendemain.")
    jours = models.CharField(
        "jours de début", max_length=7, default="01234",
        validators=[RegexValidator(r"^[0-6]{1,7}$", "Chiffres de 0 (lundi) à 6 (dimanche).")],
        help_text="Jours où le créneau commence : 0 lundi … 6 dimanche. 01234 du lundi au vendredi, 56 le weekend.",
    )
    ordre = models.PositiveSmallIntegerField(default=0)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordre", "heure_debut"]
        verbose_name = "créneau"

    def __str__(self):
        return f"{self.nom} ({self.heure_debut:%H:%M}–{self.heure_fin:%H:%M})"

    def travaille_le(self, jour):
        return str(jour.weekday()) in self.jours

    def bornes(self, jour):
        return calculs.bornes_du_creneau(jour, self.heure_debut, self.heure_fin)

    @property
    def duree(self):
        debut, fin = self.bornes(timezone.localdate())
        return calculs.duree_en_minutes(debut, fin)

    @property
    def libelle_jours(self):
        return ", ".join(JOURS_DE_LA_SEMAINE[int(chiffre)] for chiffre in self.jours)


class CauseArret(models.Model):
    """Ligne de la liste des causes, enrichie depuis le paramétrage. Une cause ne se supprime pas : elle s'archive."""

    libelle = models.CharField("libellé", max_length=80, unique=True)
    commentaire_obligatoire = models.BooleanField(default=False)
    ordre = models.PositiveSmallIntegerField(default=0)
    actif = models.BooleanField(default=True, help_text="Décoché : la cause est archivée et n'est plus proposée.")

    class Meta:
        ordering = ["ordre", "libelle"]
        verbose_name = "cause d'arrêt"
        verbose_name_plural = "causes d'arrêt"

    def __str__(self):
        return self.libelle


class Shift(models.Model):
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT, related_name="shifts")
    jour = models.DateField(help_text="Date du début du créneau : la nuit du lundi commence le lundi.")
    creneau = models.ForeignKey(Creneau, on_delete=models.PROTECT, related_name="shifts", verbose_name="créneau")
    equipe = models.ForeignKey(Equipe, on_delete=models.PROTECT, related_name="shifts", verbose_name="équipe")
    matricule = models.ForeignKey(Matricule, on_delete=models.PROTECT, null=True, blank=True, related_name="shifts",
                                  help_text="Vide pour l'historique repris de l'Excel.")
    # Copiés du créneau à l'ouverture : changer les horaires plus tard ne réécrit pas le passé.
    debut = models.DateTimeField("début")
    fin = models.DateTimeField()
    ouvert_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="+", verbose_name="ouvert par (compte)")
    ouvert_le = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-debut", "machine__code"]
        constraints = [models.UniqueConstraint(fields=["machine", "jour", "creneau"], name="shift_unique")]
        indexes = [models.Index(fields=["jour"], name="shift_jour")]

    def __str__(self):
        return f"{self.machine.code} {self.jour:%d/%m/%Y} {self.creneau.nom} {self.equipe}"

    def get_absolute_url(self):
        return reverse("shift", args=[self.pk])

    def est_termine(self, moment=None):
        return (moment or timezone.now()) >= self.fin

    def bilan(self):
        if not hasattr(self, "_bilan"):
            self._bilan = calculs.bilan_du_shift(self)
        return self._bilan

    def troncon_en_cours(self):
        troncons = sorted(self.troncons.all(), key=lambda troncon: troncon.debut)
        return troncons[-1] if troncons else None


class Troncon(models.Model):
    """Partie du shift sur un même produit, jusqu'au changement de produit suivant ou la fin du shift."""

    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="troncons")
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, related_name="troncons_production")
    debut = models.DateTimeField("début")
    compteur_debut = models.PositiveIntegerField("compteur au début", default=0,
                                                 help_text="0 si le compteur a été remis à zéro.")
    compteur_fin = models.PositiveIntegerField("compteur à la fin", null=True, blank=True)
    # Copiée de la fiche produit-machine au début : la cadence du jour reste celle du rapport.
    cadence = models.DecimalField("cadence (pièces/heure)", max_digits=8, decimal_places=1, null=True, blank=True)

    class Meta:
        ordering = ["debut"]
        verbose_name = "tronçon"

    def __str__(self):
        return f"{self.produit.reference} à {timezone.localtime(self.debut):%H:%M}"

    @property
    def quantite(self):
        return calculs.quantite(self.compteur_debut, self.compteur_fin)


class Arret(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="arrets")
    troncon = models.ForeignKey(Troncon, on_delete=models.SET_NULL, null=True, blank=True, related_name="arrets",
                                verbose_name="produit concerné")
    cause = models.ForeignKey(CauseArret, on_delete=models.PROTECT, related_name="arrets")
    duree = models.PositiveIntegerField("durée (min)", validators=[MinValueValidator(1)])
    commentaire = models.CharField(max_length=300, blank=True)
    saisi_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="+")
    saisi_le = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["saisi_le"]
        verbose_name = "arrêt"

    def __str__(self):
        return f"{self.cause} {self.duree} min"


class Correction(models.Model):
    """Trace d'une modification faite après la fin du shift."""

    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="corrections")
    par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    le = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=300)

    class Meta:
        ordering = ["-le"]

    def __str__(self):
        return self.description
