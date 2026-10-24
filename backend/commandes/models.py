from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from inventaire.models import Article, ArticleFournisseur, Fournisseur, Mouvement


class CommandeQuerySet(models.QuerySet):
    def en_cours(self):
        return self.filter(etat__in=Commande.ETATS_EN_COURS)

    def en_retard(self):
        return self.filter(etat=Commande.PASSEE, date_prevue__lt=timezone.localdate())


class Commande(models.Model):
    EN_ATTENTE = "attente"
    PASSEE = "passee"
    RECUE = "recue"
    RECEPTIONNEE = "receptionnee"
    ANNULEE = "annulee"
    ETATS = [
        (EN_ATTENTE, "En attente"),
        (PASSEE, "Passée"),
        (RECUE, "Reçue"),
        (RECEPTIONNEE, "Réceptionnée"),
        (ANNULEE, "Annulée"),
    ]
    # Tant qu'une commande est dans un de ces états, ses quantités sont attendues en stock.
    ETATS_EN_COURS = [EN_ATTENTE, PASSEE, RECUE]
    ETATS_SUIVANTS = {
        EN_ATTENTE: [PASSEE, ANNULEE],
        PASSEE: [RECUE, ANNULEE],
        RECUE: [RECEPTIONNEE],
    }

    numero = models.CharField("numéro", max_length=20, unique=True, blank=True,
                              help_text="Laisser vide pour une numérotation automatique (CDE-année-numéro).")
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT, related_name="commandes")
    etat = models.CharField("état", max_length=12, choices=ETATS, default=EN_ATTENTE)
    numero_fournisseur = models.CharField("n° de confirmation du fournisseur", max_length=40, blank=True)
    date_creation = models.DateField("créée le", default=timezone.localdate)
    date_passage = models.DateField("passée le", null=True, blank=True)
    date_prevue = models.DateField("livraison prévue le", null=True, blank=True)
    date_reception = models.DateField("reçue le", null=True, blank=True)
    date_entree_stock = models.DateField("entrée en stock le", null=True, blank=True)
    notes = models.TextField(blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="créée par")

    objects = CommandeQuerySet.as_manager()

    class Meta:
        ordering = ["-date_creation", "-numero"]

    def __str__(self):
        return f"{self.numero} – {self.fournisseur}"

    def get_absolute_url(self):
        return reverse("commande", args=[self.pk])

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = prochain_numero(self.date_creation.year)
        super().save(*args, **kwargs)

    @property
    def est_en_cours(self):
        return self.etat in self.ETATS_EN_COURS

    @property
    def etats_suivants(self):
        return self.ETATS_SUIVANTS.get(self.etat, [])

    @property
    def montant_total(self):
        return sum((ligne.montant for ligne in self.lignes.all() if ligne.montant is not None), 0)

    @property
    def jours_avant_livraison(self):
        """Jours restants avant la date prévue (négatif quand elle est dépassée) ; None sans date prévue."""
        if self.date_prevue is None:
            return None
        return (self.date_prevue - timezone.localdate()).days

    @property
    def jours_de_retard(self):
        jours = self.jours_avant_livraison
        return -jours if jours is not None and jours < 0 else 0

    @property
    def en_retard(self):
        """Une commande passée est en retard dès que sa date de livraison prévue est dépassée."""
        return self.etat == self.PASSEE and self.jours_de_retard > 0

    @property
    def livraison_proche(self):
        jours = self.jours_avant_livraison
        return self.etat == self.PASSEE and jours is not None and 0 <= jours <= 2

    @property
    def delai_jours(self):
        """Délai annoncé : de la date de passage à la date de livraison prévue."""
        if self.date_passage is None or self.date_prevue is None:
            return None
        return (self.date_prevue - self.date_passage).days

    @property
    def retard_a_la_livraison(self):
        """Pour une commande arrivée : jours de retard par rapport à la date prévue (0 si à l'heure)."""
        if self.date_reception is None or self.date_prevue is None:
            return None
        return max(0, (self.date_reception - self.date_prevue).days)

    def delai_fournisseur(self):
        """Délai le plus long du fournisseur parmi les articles de la commande, en jours ; None si inconnu."""
        articles = self.lignes.values_list("article", flat=True)
        return ArticleFournisseur.objects.filter(
            fournisseur=self.fournisseur, article__in=articles, delai__isnull=False
        ).aggregate(delai=Max("delai"))["delai"]

    @transaction.atomic
    def changer_etat(self, nouvel_etat, utilisateur=None):
        """Fait avancer la commande et note la date ; la réception fait entrer les quantités en stock."""
        if nouvel_etat not in self.etats_suivants:
            raise ValueError(f"Une commande « {self.get_etat_display()} » ne peut pas passer à « {nouvel_etat} ».")
        aujourdhui = timezone.localdate()
        if nouvel_etat == self.PASSEE:
            self.date_passage = aujourdhui
            delai = self.delai_fournisseur()
            if self.date_prevue is None and delai is not None:
                self.date_prevue = aujourdhui + timedelta(days=delai)
        elif nouvel_etat == self.RECUE:
            self.date_reception = aujourdhui
        elif nouvel_etat == self.RECEPTIONNEE:
            self.date_entree_stock = aujourdhui
            for ligne in self.lignes.select_related("article"):
                Mouvement.enregistrer(ligne.article, Mouvement.ENTREE, ligne.quantite, utilisateur=utilisateur,
                                      commentaire=f"Réception commande {self.numero}")
        self.etat = nouvel_etat
        self.save()

    @classmethod
    @transaction.atomic
    def creer_pour_les_besoins(cls, fournisseur, articles, utilisateur=None):
        """Crée une commande en attente avec, pour chaque article, la quantité qui reste à commander."""
        commande = cls.objects.create(fournisseur=fournisseur, cree_par=utilisateur)
        for article in articles:
            quantite = article.reste_a_commander
            if quantite > 0:
                LigneCommande.objects.create(commande=commande, article=article, quantite=quantite)
        return commande


def prochain_numero(annee):
    prefixe = f"CDE-{annee}-"
    dernier = (Commande.objects.filter(numero__startswith=prefixe).order_by("-numero")
               .values_list("numero", flat=True).first())
    rang = int(dernier.removeprefix(prefixe)) + 1 if dernier and dernier.removeprefix(prefixe).isdigit() else 1
    return f"{prefixe}{rang:04d}"


class LigneCommandeQuerySet(models.QuerySet):
    def en_cours(self):
        return self.filter(commande__etat__in=Commande.ETATS_EN_COURS)


class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name="lignes")
    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="lignes_commande")
    quantite = models.DecimalField("quantité", max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField("prix unitaire (€)", max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Laisser vide pour reprendre le prix du fournisseur.")

    objects = LigneCommandeQuerySet.as_manager()

    class Meta:
        ordering = ["article__reference"]
        verbose_name = "ligne de commande"
        verbose_name_plural = "lignes de commande"

    def __str__(self):
        return f"{self.quantite} × {self.article.reference}"

    def save(self, *args, **kwargs):
        if self.prix_unitaire is None:
            lien = self.lien_fournisseur
            self.prix_unitaire = lien.prix if lien else None
        super().save(*args, **kwargs)

    @property
    def lien_fournisseur(self):
        return ArticleFournisseur.objects.filter(article=self.article, fournisseur=self.commande.fournisseur).first()

    @property
    def montant(self):
        if self.prix_unitaire is None:
            return None
        return self.quantite * self.prix_unitaire


def renseigner_commandes_en_cours(articles):
    """Charge en une requête les commandes en cours des articles : article.lignes_en_cours et quantite_en_commande.

    Évite une requête par article dans les listes ; renvoie la liste des articles.
    """
    articles = list(articles)
    lignes_par_article = defaultdict(list)
    lignes = (LigneCommande.objects.en_cours().filter(article__in=articles)
              .select_related("commande").order_by("commande__date_prevue"))
    for ligne in lignes:
        lignes_par_article[ligne.article_id].append(ligne)
    for article in articles:
        article.lignes_en_cours = lignes_par_article[article.pk]
        # Remplit la valeur mise en cache par la propriété Article.quantite_en_commande.
        article.__dict__["quantite_en_commande"] = sum((ligne.quantite for ligne in article.lignes_en_cours), 0)
    return articles
