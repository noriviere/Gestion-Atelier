from django.db import migrations

INTENDANT = "Intendant"


def creer_groupe(apps, schema_editor):
    apps.get_model("auth", "Group").objects.get_or_create(name=INTENDANT)


def supprimer_groupe(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name=INTENDANT).delete()


class Migration(migrations.Migration):
    dependencies = [("comptes", "0001_groupes")]
    operations = [migrations.RunPython(creer_groupe, supprimer_groupe)]
