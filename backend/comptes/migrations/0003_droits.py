from django.db import migrations, models
import django.db.models.deletion

from comptes.droits import DEFAUTS

ANCIEN_PROFIL_ATELIER = "Régleur et opérateur"


def separer_les_profils_et_donner_les_droits_de_depart(apps, schema_editor):
    """L'ancien profil commun devient Opérateur ; chaque profil reçoit ses droits de départ."""
    Group = apps.get_model("auth", "Group")
    Droit = apps.get_model("comptes", "Droit")
    # (configurer_permissions fait de même après chaque migration, pour les bases déjà migrées.)
    if not Group.objects.filter(name="Opérateur").exists():
        Group.objects.filter(name=ANCIEN_PROFIL_ATELIER).update(name="Opérateur")
    for nom, codes in DEFAUTS.items():
        groupe, _ = Group.objects.get_or_create(name=nom)
        Droit.objects.bulk_create([Droit(profil=groupe, code=code) for code in codes], ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("comptes", "0002_groupe_intendant")]
    operations = [
        migrations.CreateModel(
            name="Droit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50)),
                ("profil", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="droits", to="auth.group")),
            ],
            options={"ordering": ["profil__name", "code"]},
        ),
        migrations.AddConstraint(
            model_name="droit",
            constraint=models.UniqueConstraint(fields=("profil", "code"), name="droit_unique_par_profil"),
        ),
        migrations.RunPython(separer_les_profils_et_donner_les_droits_de_depart, migrations.RunPython.noop),
    ]
