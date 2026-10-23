from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


class Fournisseur(models.Model):
    nom = models.CharField(max_length=120, unique=True)
    contact = models.CharField(max_length=120, blank=True)
    telephone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class TypeInventaire(models.Model):
    """Regroupe les articles comptés ensemble (par zone, par famille...)."""

    nom = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "type d'inventaire"
        verbose_name_plural = "types d'inventaire"

    def __str__(self):
        return self.nom


class Article(models.Model):
    PIECE_USURE = "usure"
    CONSOMMABLE = "conso"
    CATEGORIES = [(PIECE_USURE, "Pièce d'usure"), (CONSOMMABLE, "Consommable")]

    reference = models.CharField(max_length=40, unique=True)
    designation = models.CharField(max_length=160)
    categorie = models.CharField(max_length=5, choices=CATEGORIES, default=PIECE_USURE)
    type_inventaire = models.ForeignKey(TypeInventaire, on_delete=models.PROTECT, related_name="articles")
    emplacement = models.CharField(max_length=60, blank=True)
    unite = models.CharField(max_length=20, default="pièce")
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_mini = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mini_commande = models.DecimalField("quantité mini de commande", max_digits=10, decimal_places=2, default=1)
    frequence_inventaire = models.PositiveIntegerField("fréquence d'inventaire (jours)", default=90)
    dernier_inventaire = models.DateField(null=True, blank=True)
    fournisseurs = models.ManyToManyField(Fournisseur, through="ArticleFournisseur", related_name="articles")

    class Meta:
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference} – {self.designation}"

    def get_absolute_url(self):
        return reverse("article", args=[self.pk])

    @property
    def a_commander(self):
        return self.stock <= self.stock_mini

    @property
    def quantite_a_commander(self):
        """Ramène le stock au-dessus du mini, sans descendre sous le mini de commande."""
        if not self.a_commander:
            return 0
        return max(self.mini_commande, self.stock_mini - self.stock + self.mini_commande)

    @property
    def prochain_inventaire(self):
        if self.dernier_inventaire is None:
            return None
        return self.dernier_inventaire + timedelta(days=self.frequence_inventaire)

    @property
    def inventaire_du(self):
        prochain = self.prochain_inventaire
        return prochain is None or prochain <= timezone.localdate()

    @property
    def fournisseur_prefere(self):
        lien = self.liens_fournisseurs.filter(prefere=True).select_related("fournisseur").first()
        return lien.fournisseur if lien else None


class ArticleFournisseur(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="liens_fournisseurs")
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name="liens_articles")
    reference_fournisseur = models.CharField(max_length=60, blank=True)
    prix = models.DecimalField("prix unitaire (€)", max_digits=10, decimal_places=2, null=True, blank=True)
    delai = models.PositiveIntegerField("délai (jours)", null=True, blank=True)
    prefere = models.BooleanField("fournisseur préféré", default=False)

    class Meta:
        ordering = ["-prefere", "fournisseur__nom"]
        unique_together = [("article", "fournisseur")]
        constraints = [
            models.UniqueConstraint(
                fields=["article"], condition=models.Q(prefere=True), name="un_seul_fournisseur_prefere"
            )
        ]
        verbose_name = "fournisseur de l'article"
        verbose_name_plural = "fournisseurs de l'article"

    def __str__(self):
        return f"{self.article.reference} chez {self.fournisseur}"


class Mouvement(models.Model):
    ENTREE = "entree"
    SORTIE = "sortie"
    INVENTAIRE = "inventaire"
    TYPES = [(ENTREE, "Entrée"), (SORTIE, "Sortie"), (INVENTAIRE, "Comptage d'inventaire")]

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="mouvements")
    type = models.CharField(max_length=10, choices=TYPES)
    quantite = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Pour un comptage : la quantité comptée."
    )
    stock_apres = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(default=timezone.now)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    commentaire = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_display()} {self.quantite} {self.article.reference}"

    @classmethod
    @transaction.atomic
    def enregistrer(cls, article, type, quantite, utilisateur=None, commentaire=""):
        """Crée le mouvement et met à jour le stock de l'article."""
        article = Article.objects.select_for_update().get(pk=article.pk)
        if type == cls.ENTREE:
            article.stock += quantite
        elif type == cls.SORTIE:
            article.stock -= quantite
        else:
            article.stock = quantite
            article.dernier_inventaire = timezone.localdate()
        article.save()
        return cls.objects.create(
            article=article,
            type=type,
            quantite=quantite,
            stock_apres=article.stock,
            utilisateur=utilisateur,
            commentaire=commentaire,
        )
