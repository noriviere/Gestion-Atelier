from django.db import migrations

GROUPES = ["Admin", "Méthode et management", "Régleur et opérateur"]


def creer_groupes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nom in GROUPES:
        Group.objects.get_or_create(name=nom)


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(creer_groupes, migrations.RunPython.noop)]
