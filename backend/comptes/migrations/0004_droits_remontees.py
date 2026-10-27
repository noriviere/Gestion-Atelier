from django.db import migrations

# Droits du bloc « Remontées terrain » donnés aux profils déjà réglés sur la page « Droits ».
# Les codes sont écrits ici, et non lus dans droits.DEFAUTS, pour que la migration ne change pas plus tard.
SAISIR_ET_CONSULTER = ["remontees_saisir", "remontees_consulter"]
CODES_PAR_PROFIL = {
    "Méthode et management": SAISIR_ET_CONSULTER + ["remontees_parametrer"],
    "Intendant": SAISIR_ET_CONSULTER,
    "Régleur": SAISIR_ET_CONSULTER,
    "Opérateur": SAISIR_ET_CONSULTER,
}


def donner_les_droits(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Droit = apps.get_model("comptes", "Droit")
    for nom, codes in CODES_PAR_PROFIL.items():
        groupe = Group.objects.filter(name=nom).first()
        if groupe:
            Droit.objects.bulk_create([Droit(profil=groupe, code=code) for code in codes], ignore_conflicts=True)


def retirer_les_droits(apps, schema_editor):
    apps.get_model("comptes", "Droit").objects.filter(code__startswith="remontees_").delete()


class Migration(migrations.Migration):
    dependencies = [("comptes", "0003_droits")]
    operations = [migrations.RunPython(donner_les_droits, retirer_les_droits)]
