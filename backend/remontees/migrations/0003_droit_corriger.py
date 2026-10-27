from django.db import migrations

# Le droit de corriger une saisie meule, donné au profil Méthode et management déjà réglé sur la page « Droits ».
# Cette migration est dans l'application remontees pour rester indépendante des autres droits ajoutés à comptes.


def donner_le_droit(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Droit = apps.get_model("comptes", "Droit")
    groupe = Group.objects.filter(name="Méthode et management").first()
    if groupe:
        Droit.objects.get_or_create(profil=groupe, code="remontees_corriger")


def retirer_le_droit(apps, schema_editor):
    apps.get_model("comptes", "Droit").objects.filter(code="remontees_corriger").delete()


class Migration(migrations.Migration):
    dependencies = [("remontees", "0002_regles_themes_corrections"), ("comptes", "0004_droits_remontees")]
    operations = [migrations.RunPython(donner_le_droit, retirer_le_droit)]
