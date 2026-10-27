"""Remontées du terrain : matricules, table « formats et matière » et saisies d'usure des meules.

Reprise de l'application suivi-usure-meules : les colonnes que le classeur Excel calculait
par formules sont ici des propriétés des saisies.
"""
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from inventaire.models import Article, Mouvement
from produits.models import Machine, Produit

from . import regles

LONGUEUR_MATRICULE = 4


class Matricule(models.Model):
    """Matricule de la personne qui monte ou démonte : choisi dans la liste, ou ajouté à la saisie."""

    numero = models.CharField(
        "numéro", max_length=LONGUEUR_MATRICULE, unique=True,
        validators=[RegexValidator(rf"^\d{{{LONGUEUR_MATRICULE}}}$", f"{LONGUEUR_MATRICULE} chiffres.")],
    )
    nom = models.CharField(max_length=80, blank=True)
    actif = models.BooleanField(default=True, help_text="Décoché : n'est plus proposé dans les listes.")

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"{self.numero} – {self.nom}" if self.nom else self.numero

    @staticmethod
    def normaliser(texte):
        """« 534 » -> « 0534 » : les numéros trop courts sont complétés par des zéros, comme dans l'ancienne application."""
        texte = str(texte or "").strip()
        if texte.isdigit() and len(texte) < LONGUEUR_MATRICULE:
            texte = texte.zfill(LONGUEUR_MATRICULE)
        return texte


class FormatMatiere(models.Model):
    """Ligne de l'onglet « Formats & matière » : ce qui est prévu pour un produit dans une matière."""

    INOX = "I"
    CARBONE = "C"
    MATIERES = [(INOX, "Inox"), (CARBONE, "Carbone")]
    MA5_OUI = "oui"
    MA5_NON = "non"
    MA5_PEUT_ETRE = "peut_etre"
    CHOIX_MA5 = [(MA5_OUI, "Oui"), (MA5_NON, "Non"), (MA5_PEUT_ETRE, "Peut-être (choisi à la saisie)")]

    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, related_name="formats_meule",
                                help_text="Le format du classeur : c'est le produit.")
    matiere = models.CharField("matière", max_length=1, choices=MATIERES)
    code_lame = models.CharField(max_length=40, blank=True)
    ma5 = models.CharField("MA5", max_length=10, choices=CHOIX_MA5, default=MA5_NON)
    meules = models.ManyToManyField(Article, blank=True, related_name="formats_meule",
                                    verbose_name="meules prévues")
    machines = models.ManyToManyField(Machine, blank=True, related_name="formats_meule",
                                      verbose_name="machines prévues",
                                      help_text="Vide : toutes les machines sont acceptées.")

    class Meta:
        ordering = ["produit__reference", "matiere"]
        constraints = [models.UniqueConstraint(fields=["produit", "matiere"], name="format_matiere_unique")]
        verbose_name = "format et matière"
        verbose_name_plural = "formats et matière"

    def __str__(self):
        return f"{self.produit.reference} {self.get_matiere_display()}"


class SaisieMeuleQuerySet(models.QuerySet):
    def montees(self):
        """Meules montées et pas encore démontées."""
        return self.filter(demonte_le__isnull=True)

    def demontees(self):
        return self.filter(demonte_le__isnull=False)


class SaisieMeule(models.Model):
    """Une meule, de son montage à son démontage : la ligne de l'onglet « Data » du classeur."""

    FACES = [("A", "A"), ("B", "B")]

    # Montage (fiche du monteur)
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT, related_name="saisies_meules")
    format_matiere = models.ForeignKey(FormatMatiere, on_delete=models.PROTECT, related_name="saisies",
                                       verbose_name="format et matière")
    face = models.CharField(max_length=1, choices=FACES)
    meule = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="saisies_meules",
                              verbose_name="n° article meule")
    lot_fournisseur = models.CharField("lot fournisseur / n° FA / Beleg", max_length=60)
    date_montage = models.DateField("date de montage", default=timezone.localdate)
    ma5 = models.BooleanField("MA5", default=False)
    pression_arrosage = models.PositiveIntegerField("pression d'arrosage", default=6)
    vitesse_rotation = models.PositiveIntegerField("vitesse de rotation (m/s)")
    vitesse_avance = models.PositiveIntegerField("vitesse d'avance (mm/min)")
    hauteur_initiale = models.DecimalField("hauteur initiale de la meule (mm)", max_digits=6, decimal_places=2,
                                           validators=[MinValueValidator(0)])
    compteur_debut = models.PositiveIntegerField("compteur machine au montage", default=0)
    matricule_monteur = models.ForeignKey(Matricule, on_delete=models.PROTECT, related_name="montages")
    commentaire_montage = models.TextField("commentaire au montage", blank=True)
    monte_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name="+", verbose_name="saisi par (compte)")
    monte_le = models.DateTimeField("montage saisi le", default=timezone.now)
    sortie_stock = models.ForeignKey(Mouvement, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    # Démontage
    matricule_demonteur = models.ForeignKey(Matricule, on_delete=models.PROTECT, null=True, blank=True,
                                            related_name="demontages")
    compteur_fin = models.PositiveIntegerField("compteur machine au démontage", null=True, blank=True)
    hauteur_finale = models.DecimalField("hauteur finale de la meule (mm)", max_digits=6, decimal_places=2,
                                         null=True, blank=True, validators=[MinValueValidator(0)])
    probleme = models.BooleanField("problème signalé", default=False)
    themes = models.JSONField("thèmes du problème", default=list, blank=True)
    commentaire = models.TextField(blank=True)
    demonte_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+", verbose_name="démontage saisi par (compte)")
    demonte_le = models.DateTimeField("démontage saisi le", null=True, blank=True)
    non_finie = models.BooleanField("démontée avant usure totale", default=False,
                                    help_text="La marque « X » : il restait plus que le seuil au démontage.")
    defaut = models.BooleanField("meule défectueuse", default=False,
                                 help_text="Cassée ou fissurée et démontée avant usure : l'onglet « Data défaut ».")

    # Avertissements que la personne a lus puis confirmés, gardés pour le contrôle qualité.
    avertissements = models.TextField(blank=True)
    corrige_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+", verbose_name="corrigé par")
    corrige_le = models.DateTimeField("corrigé le", null=True, blank=True)

    objects = SaisieMeuleQuerySet.as_manager()

    class Meta:
        ordering = ["-date_montage", "-monte_le"]
        indexes = [
            models.Index(fields=["machine", "demonte_le"], name="saisie_meule_machine"),
            models.Index(fields=["meule", "format_matiere"], name="saisie_meule_reference"),
        ]
        verbose_name = "saisie meule"
        verbose_name_plural = "saisies meules"

    def __str__(self):
        return f"Meule {self.meule.reference} face {self.face} sur {self.machine.code} ({self.date_montage:%d/%m/%Y})"

    def get_absolute_url(self):
        return reverse("saisie_meule", args=[self.pk])

    @property
    def est_demontee(self):
        return self.demonte_le is not None

    @property
    def code_lame(self):
        return self.format_matiere.code_lame

    # --- Colonnes calculées par les formules du classeur ---------------------------------------
    @property
    def nombre_faces_brut(self):
        return regles.nombre_faces_brut(self.compteur_debut, self.compteur_fin)

    @property
    def hauteur_usee(self):
        return regles.hauteur_usee(self.hauteur_initiale, self.hauteur_finale)

    @property
    def faces_par_mm(self):
        return regles.faces_par_mm(self.nombre_faces_brut, self.hauteur_usee)

    @property
    def faces_par_meule_reference(self):
        """« Nb faces/meule de 89 mm » : la durée de vie ramenée à une meule de hauteur de référence."""
        return regles.faces_par_meule_reference(self.faces_par_mm)

    @property
    def hauteur_usee_par_face(self):
        return regles.hauteur_usee_par_face(self.nombre_faces_brut, self.hauteur_usee)

    def marquer(self, reglages):
        """Pose les marques du démontage : X (non finie) et défaut, avec les règles du moment."""
        self.non_finie = regles.demontee_avant_usure(self.hauteur_finale, reglages)
        self.defaut = regles.est_un_defaut(self.probleme, self.themes, self.hauteur_finale, reglages)


class RegleMeule(models.Model):
    """Réglage d'une règle du catalogue (regles.CATALOGUE) : interrupteur et valeurs, en texte décimal."""

    code = models.CharField(max_length=40, unique=True)
    actif = models.BooleanField(default=True)
    valeurs = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "règle des meules"
        verbose_name_plural = "règles des meules"

    def __str__(self):
        regle = regles.PAR_CODE.get(self.code)
        return regle.titre if regle else self.code


class HistoriqueRegle(models.Model):
    """Chaque changement fait dans le back-office des règles : qui, quand, quoi."""

    date = models.DateTimeField(default=timezone.now)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    texte = models.CharField(max_length=300)

    class Meta:
        ordering = ["-date", "-pk"]
        verbose_name = "changement de règle"
        verbose_name_plural = "historique des règles"

    def __str__(self):
        return self.texte


class ThemeProbleme(models.Model):
    """Thème proposé à la question « Qu'est-ce qui a posé problème ? » du démontage."""

    libelle = models.CharField("libellé", max_length=80, unique=True)
    ordre = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["ordre", "libelle"]
        verbose_name = "thème de problème"
        verbose_name_plural = "thèmes de problème"

    def __str__(self):
        return self.libelle
