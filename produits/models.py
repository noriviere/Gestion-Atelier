from django.db import models
from django.urls import reverse

from inventaire.models import Article
from outillage.models import Outil


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


class ProduitMachine(models.Model):
    """Fabrication d'un produit sur une machine : c'est le contenu de la fiche."""

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="fabrications")
    machine = models.ForeignKey(Machine, on_delete=models.PROTECT, related_name="fabrications")
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
