from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.urls import reverse

from inventaire.models import Article
from outillage.models import Outil

EXTENSIONS_IMAGES = ["jpg", "jpeg", "png", "gif", "webp", "svg"]
EXTENSIONS_DOCUMENTS = ["pdf", "doc", "docx", "xls", "xlsx", "odt", "ods", "txt", "dxf", "dwg"]
TAILLE_MAXI_DOCUMENT = 20 * 1024 * 1024


class Machine(models.Model):
    code = models.CharField(max_length=40, unique=True)
    nom = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.nom}"

    def get_absolute_url(self):
        return reverse("machine", args=[self.pk])


class Produit(models.Model):
    reference = models.CharField(max_length=40, unique=True)
    designation = models.CharField(max_length=160)
    client = models.CharField(max_length=120, blank=True)
    notes = models.TextField("notes générales", blank=True)
    machines = models.ManyToManyField(Machine, through="ProduitMachine", related_name="produits")

    class Meta:
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference} – {self.designation}"

    def get_absolute_url(self):
        return reverse("produit", args=[self.pk])

    @transaction.atomic
    def dupliquer(self, reference, designation):
        """Nouveau produit avec les mêmes notes, documents et fiches par machine (états compris)."""
        copie = Produit.objects.create(reference=reference, designation=designation, client=self.client, notes=self.notes)
        for document in self.documents.filter(fabrication__isnull=True):
            document.copier_vers(copie)
        for fabrication in self.fabrications.all():
            fabrication.copier_vers(copie, fabrication.machine, fabrication.etat)
        return copie


class ProduitMachine(models.Model):
    """Un produit face à une machine : sa case dans la matrice et, s'il y est fabriqué, le contenu de sa fiche."""

    PROGRAMME = "programme"
    A_FAIRE = "a_faire"
    NON_FAISABLE = "non_faisable"
    POSSIBLE = "possible"
    ETATS = [
        (PROGRAMME, "Programmé"),
        (A_FAIRE, "À faire"),
        (NON_FAISABLE, "Non faisable"),
        (POSSIBLE, "Possible, rien de prévu"),
    ]
    # États qui donnent une fiche de production (les autres ne servent qu'à la matrice).
    ETATS_AVEC_FICHE = [PROGRAMME, A_FAIRE]

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="fabrications")
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT, related_name="fabrications")
    etat = models.CharField("état", max_length=20, choices=ETATS, default=PROGRAMME)
    cadence = models.DecimalField("cadence (pièces/heure)", max_digits=8, decimal_places=1, null=True, blank=True)
    outils = models.ManyToManyField(Outil, blank=True, related_name="fabrications")
    notes = models.TextField("notes de réglage et de production", blank=True)

    class Meta:
        ordering = ["produit__reference", "machine__code"]
        unique_together = [("produit", "machine")]
        verbose_name = "produit sur machine"
        verbose_name_plural = "produits sur machine"

    def __str__(self):
        return f"{self.produit.reference} sur {self.machine.code}"

    def get_absolute_url(self):
        return reverse("fiche", args=[self.pk])

    @classmethod
    def changer_etat(cls, produit, machine, etat):
        """Change l'état d'une case de la matrice ; renvoie la ligne, ou None si la case redevient vide.

        Une case vidée garde sa fiche si elle contient déjà des saisies : elle passe « possible ».
        """
        case = cls.objects.filter(produit=produit, machine=machine).first()
        if not etat:
            if case and case.est_vide():
                case.delete()
                return None
            etat = cls.POSSIBLE
            if not case:
                return None
        if etat not in dict(cls.ETATS):
            raise ValueError(f"État inconnu : {etat}.")
        if case:
            case.etat = etat
            case.save(update_fields=["etat"])
            return case
        return cls.objects.create(produit=produit, machine=machine, etat=etat)

    @property
    def a_une_fiche(self):
        return self.etat in self.ETATS_AVEC_FICHE

    def est_vide(self):
        """Vrai quand rien n'a encore été saisi : la ligne peut être supprimée sans rien perdre."""
        return (self.cadence is None and not self.notes and not self.outils.exists()
                and not self.consommations.exists() and not self.parametres.exists() and not self.documents.exists())

    def copier_vers(self, produit, machine, etat, avec_documents=True):
        """Copie cadence, outils, consommables, paramètres, notes et documents de la fiche vers (produit, machine).

        La fiche cible est créée si besoin ; si elle existe déjà, son contenu est remplacé.
        Les photos d'une fiche montrent le réglage d'une machine : on ne les reprend pas vers une autre machine.
        """
        cible, _ = ProduitMachine.objects.update_or_create(
            produit=produit, machine=machine,
            defaults={"etat": etat, "cadence": self.cadence, "notes": self.notes},
        )
        cible.outils.set(self.outils.all())
        cible.consommations.all().delete()
        cible.parametres.all().delete()
        Consommation.objects.bulk_create(
            Consommation(fabrication=cible, article_id=consommation.article_id, quantite=consommation.quantite)
            for consommation in self.consommations.all()
        )
        Parametre.objects.bulk_create(
            Parametre(fabrication=cible, libelle=parametre.libelle, valeur=parametre.valeur, unite=parametre.unite,
                      ordre=parametre.ordre)
            for parametre in self.parametres.all()
        )
        if avec_documents:
            for document in self.documents.all():
                document.copier_vers(produit, cible)
        return cible

    @transaction.atomic
    def dupliquer_vers_machine(self, machine):
        """Fiche du même produit sur une autre machine, à valider : elle passe « à faire » (ou reste programmée)."""
        if machine.pk == self.machine_id:
            raise ValueError("Choisissez une autre machine que celle de la fiche d'origine.")
        existante = ProduitMachine.objects.filter(produit=self.produit, machine=machine).first()
        if existante and existante.a_une_fiche and not existante.est_vide():
            raise ValueError(f"{self.produit.reference} a déjà une fiche remplie sur {machine.code}.")
        etat = existante.etat if existante and existante.etat == self.PROGRAMME else self.A_FAIRE
        return self.copier_vers(self.produit, machine, etat, avec_documents=False)


class Consommation(models.Model):
    fabrication = models.ForeignKey(ProduitMachine, on_delete=models.CASCADE, related_name="consommations")
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="consommations")
    quantite = models.CharField("quantité / fréquence", max_length=80, blank=True, help_text="Ex. : 1 par équipe")

    class Meta:
        unique_together = [("fabrication", "article")]
        verbose_name = "consommable utilisé"
        verbose_name_plural = "consommables utilisés"

    def __str__(self):
        return f"{self.article.reference} ({self.quantite})"


class Parametre(models.Model):
    """Paramètre de réglage de la fiche : un libellé, une valeur et son unité (ex. Vitesse meule, 35, m/s)."""

    fabrication = models.ForeignKey(ProduitMachine, on_delete=models.CASCADE, related_name="parametres")
    libelle = models.CharField("paramètre", max_length=80)
    valeur = models.CharField(max_length=80)
    unite = models.CharField("unité", max_length=20, blank=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "pk"]
        verbose_name = "paramètre de réglage"
        verbose_name_plural = "paramètres de réglage"

    def __str__(self):
        return f"{self.libelle} : {self.valeur} {self.unite}".strip()


def chemin_document(document, nom_fichier):
    return f"documents/{document.produit.reference}/{nom_fichier}"


class Document(models.Model):
    """Plan, photo de réglage, consigne… rattaché au produit (toutes ses fiches) ou à une seule fiche."""

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="documents")
    fabrication = models.ForeignKey(ProduitMachine, on_delete=models.CASCADE, null=True, blank=True,
                                    related_name="documents",
                                    help_text="Vide : le document concerne le produit sur toutes les machines.")
    titre = models.CharField(max_length=160)
    fichier = models.FileField(
        upload_to=chemin_document, max_length=255,
        validators=[FileExtensionValidator(EXTENSIONS_IMAGES + EXTENSIONS_DOCUMENTS)],
    )
    ajoute_le = models.DateTimeField("ajouté le", auto_now_add=True)
    ajoute_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="+")

    class Meta:
        ordering = ["fabrication_id", "titre"]

    def __str__(self):
        return self.titre

    @property
    def nom_fichier(self):
        return Path(self.fichier.name).name

    @property
    def extension(self):
        return Path(self.fichier.name).suffix.lower().lstrip(".")

    @property
    def est_une_image(self):
        return self.extension in EXTENSIONS_IMAGES

    def get_absolute_url(self):
        return reverse("document", args=[self.pk, self.nom_fichier])

    def copier_vers(self, produit, fabrication=None):
        """Même fichier, rattaché ailleurs : le fichier n'est pas recopié sur le disque."""
        return Document.objects.create(produit=produit, fabrication=fabrication, titre=self.titre,
                                       fichier=self.fichier.name, ajoute_par=self.ajoute_par)
