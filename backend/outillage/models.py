from django.db import models
from django.urls import reverse

from inventaire.models import Article


class Outil(models.Model):
    """Un outil ou un sous-ensemble d'outil (quand parent est renseigné)."""

    code = models.CharField(max_length=40, unique=True)
    nom = models.CharField(max_length=160)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="sous_ensembles"
    )
    description = models.TextField(blank=True)
    pieces = models.ManyToManyField(Article, through="PieceOutil", related_name="outils")

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.nom}"

    def get_absolute_url(self):
        return reverse("outil", args=[self.pk])

    def racine(self):
        outil = self
        while outil.parent_id:
            outil = outil.parent
        return outil

    def chemin(self):
        """Liste des ancêtres, de la racine jusqu'à l'outil lui-même."""
        chemin = [self]
        while chemin[0].parent_id:
            chemin.insert(0, chemin[0].parent)
        return chemin

    def descendants(self):
        """Tous les sous-ensembles, à tous les niveaux (une requête par niveau de profondeur)."""
        resultat = []
        niveau = list(self.sous_ensembles.all())
        while niveau:
            resultat.extend(niveau)
            niveau = list(Outil.objects.filter(parent__in=niveau))
        return resultat


class PieceOutil(models.Model):
    outil = models.ForeignKey(Outil, on_delete=models.CASCADE, related_name="liens_pieces")
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="liens_outils")
    quantite = models.PositiveIntegerField("quantité montée", default=1)

    class Meta:
        unique_together = [("outil", "article")]
        verbose_name = "pièce d'usure de l'outil"
        verbose_name_plural = "pièces d'usure de l'outil"

    def __str__(self):
        return f"{self.quantite} × {self.article.reference}"
