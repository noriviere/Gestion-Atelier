from django.contrib.auth.models import Group
from django.db import models


class Droit(models.Model):
    """Une sous-fonction du catalogue (comptes/droits.py) accordée à un profil."""

    profil = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="droits")
    code = models.CharField(max_length=50)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["profil", "code"], name="droit_unique_par_profil")]
        ordering = ["profil__name", "code"]

    def __str__(self):
        return f"{self.profil.name} : {self.code}"
