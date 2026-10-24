from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property


class Fournisseur(models.Model):
    nom = models.CharField(max_length=120, unique=True)
    contact = models.CharField(max_length=120, blank=True)
    telephone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse("fournisseur", args=[self.pk])


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
    ACHAT = "achat"
    DESIGN_INTERNE = "interne"
    ORIGINES = [(ACHAT, "Article acheté"), (DESIGN_INTERNE, "Design interne")]

    reference = models.CharField(max_length=40, unique=True)
    designation = models.CharField(max_length=160)
    categorie = models.CharField(max_length=5, choices=CATEGORIES, default=PIECE_USURE)
    origine = models.CharField(
        max_length=7, choices=ORIGINES, default=ACHAT,
        help_text="Acheté : identifié par la référence du fournisseur. Design interne : identifié par son numéro de plan.",
    )
    numero_plan = models.CharField("numéro de plan", max_length=60, blank=True)
    type_inventaire = models.ForeignKey(TypeInventaire, on_delete=models.PROTECT, related_name="articles")
    emplacement = models.CharField(max_length=60, blank=True)
    unite = models.CharField(max_length=20, default="pièce")
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_mini = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    mini_commande = models.DecimalField("quantité mini de commande", max_digits=10, decimal_places=2, default=1,
                                        validators=[MinValueValidator(0)])
    frequence_inventaire = models.PositiveIntegerField("fréquence d'inventaire (jours)", default=90)
    dernier_inventaire = models.DateField(null=True, blank=True)
    fournisseurs = models.ManyToManyField(Fournisseur, through="ArticleFournisseur", related_name="articles")

    class Meta:
        ordering = ["reference"]
        constraints = [
            models.CheckConstraint(condition=models.Q(stock_mini__gte=0), name="stock_mini_positif"),
            models.CheckConstraint(condition=models.Q(mini_commande__gte=0), name="mini_commande_positif"),
        ]

    def __str__(self):
        return f"{self.reference} – {self.designation}"

    def get_absolute_url(self):
        return reverse("article", args=[self.pk])

    def clean(self):
        if self.est_design_interne and not self.numero_plan.strip():
            raise ValidationError({"numero_plan": "Un article de design interne doit avoir son numéro de plan."})
        if not self.est_design_interne:
            self.numero_plan = ""

    @property
    def est_design_interne(self):
        return self.origine == self.DESIGN_INTERNE

    @property
    def a_commander(self):
        return self.stock <= self.stock_mini

    @property
    def quantite_a_commander(self):
        """Ramène le stock au-dessus du mini, sans descendre sous le mini de commande."""
        if not self.a_commander:
            return 0
        return max(self.mini_commande, self.stock_mini - self.stock + self.mini_commande)

    @cached_property
    def quantite_en_commande(self):
        """Quantité commandée et pas encore entrée en stock (commandes en attente, passées ou reçues)."""
        from commandes.models import LigneCommande  # import local : l'application commandes dépend d'inventaire

        total = LigneCommande.objects.en_cours().filter(article=self).aggregate(total=Sum("quantite"))["total"]
        return total or 0

    @property
    def stock_previsionnel(self):
        return self.stock + self.quantite_en_commande

    @property
    def couvert_par_commande(self):
        """Sous le mini, mais les commandes en cours le remonteront au-dessus."""
        return self.a_commander and self.stock_previsionnel > self.stock_mini

    @property
    def reste_a_commander(self):
        """Quantité à commander en plus des commandes en cours."""
        if not self.a_commander or self.couvert_par_commande:
            return 0
        return max(self.mini_commande, self.stock_mini - self.stock_previsionnel + self.mini_commande)

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

    @property
    def prix_de_reference(self):
        """Prix du fournisseur préféré, à défaut le plus bas connu ; sert à chiffrer les écarts d'inventaire."""
        liens = list(self.liens_fournisseurs.all())
        prix_connus = [lien.prix for lien in liens if lien.prix is not None]
        prix_prefere = next((lien.prix for lien in liens if lien.prefere and lien.prix is not None), None)
        return prix_prefere if prix_prefere is not None else min(prix_connus, default=None)


class ArticleFournisseur(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="liens_fournisseurs")
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE, related_name="liens_articles")
    reference_fournisseur = models.CharField(
        max_length=60, blank=True, help_text="Pour un article acheté. Un design interne est commandé sur son numéro de plan."
    )
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

    @property
    def reference_a_commander(self):
        """Ce qui identifie la pièce auprès du fournisseur : le plan pour un design interne, sinon sa référence."""
        if self.article.est_design_interne:
            return f"Plan {self.article.numero_plan}"
        return self.reference_fournisseur


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
    ecart = models.DecimalField(
        "écart", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Pour un comptage : quantité comptée moins stock théorique (négatif = manquant).",
    )
    date = models.DateTimeField(default=timezone.now)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    commentaire = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-date"]
        # Fiche article (derniers mouvements) et rapport des écarts (comptages par période).
        indexes = [
            models.Index(fields=["article", "-date"], name="mouvement_article_date"),
            models.Index(fields=["type", "date"], name="mouvement_type_date"),
        ]

    def __str__(self):
        return f"{self.get_type_display()} {self.quantite} {self.article.reference}"

    @property
    def stock_theorique(self):
        """Pour un comptage : le stock enregistré juste avant."""
        if self.ecart is None:
            return None
        return self.quantite - self.ecart

    @property
    def valeur_ecart(self):
        prix = self.article.prix_de_reference
        if self.ecart is None or prix is None:
            return None
        return self.ecart * prix

    @classmethod
    @transaction.atomic
    def enregistrer(cls, article, type, quantite, utilisateur=None, commentaire=""):
        """Crée le mouvement et met à jour le stock de l'article."""
        article = Article.objects.select_for_update().get(pk=article.pk)
        ecart = None
        if type == cls.ENTREE:
            article.stock += quantite
        elif type == cls.SORTIE:
            article.stock -= quantite
        else:
            ecart = quantite - article.stock
            article.stock = quantite
            article.dernier_inventaire = timezone.localdate()
        article.save()
        return cls.objects.create(
            article=article,
            type=type,
            quantite=quantite,
            stock_apres=article.stock,
            ecart=ecart,
            utilisateur=utilisateur,
            commentaire=commentaire,
        )
