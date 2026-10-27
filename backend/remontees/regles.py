"""Calculs et contrôles des saisies meules, repris de l'application suivi-usure-meules.

Les valeurs des règles sont celles de son fichier config/champs.json ; elles deviendront
réglables dans le back-office (étape 2). Les contrôles renvoient deux listes de textes :
les erreurs, qui bloquent l'enregistrement, et les avertissements, qui demandent seulement
une confirmation.
"""
import statistics
from decimal import Decimal

from django.utils import timezone

REGLAGES = {
    # Meule démontée avant usure totale au-delà de ce seuil : marquée « X », commentaire obligatoire.
    "seuil_non_finie_mm": Decimal("2"),
    # Limites bloquantes.
    "vitesse_rotation_max": 50,
    "vitesse_avance_max": 1000,
    "hauteur_initiale_max": Decimal("110"),
    # Valeur inhabituelle (règle de Tukey) : coefficient et nombre de saisies minimum pour juger.
    "habitude_coefficient": 1.5,
    "habitude_minimum": 20,
    # Le compteur fin se compare aux saisies de la même meule et matière, souvent moins nombreuses.
    "habitude_minimum_compteur": 8,
    # « Nb faces/meule de 89 mm ».
    "hauteur_reference_mm": 89,
}

THEME_DEFAUT = "Meule cassée ou fissurée"
THEMES = [
    "Bruit / vibrations",
    THEME_DEFAUT,
    "Usure irrégulière",
    "Mauvaise qualité de coupe",
    "Problème d'arrosage",
    "Réglage / machine",
    "Fiche du monteur incomplète ou illisible",
    "Autre",
]
# Aide à la rédaction du commentaire : chaque bouton ajoute son amorce.
AIDE_COMMENTAIRE = [
    ("Que s'est-il passé ?", "Constat : "),
    ("À quel moment ?", "Moment : "),
    ("Qu'avez-vous fait ensuite ?", "Action : "),
    ("Est-ce déjà arrivé ?", "Récurrence : "),
]


# --- Colonnes calculées (formules du classeur) -------------------------------------------------
def nombre_faces_brut(compteur_debut, compteur_fin):
    if compteur_fin is None or compteur_debut is None:
        return None
    return compteur_fin - compteur_debut


def hauteur_usee(hauteur_initiale, hauteur_finale):
    if hauteur_initiale is None or hauteur_finale is None:
        return None
    return hauteur_initiale - hauteur_finale


def faces_par_mm(faces, usure):
    if faces is None or not usure:
        return None
    return Decimal(faces) / usure


def faces_par_meule_reference(faces_mm):
    return None if faces_mm is None else faces_mm * REGLAGES["hauteur_reference_mm"]


def hauteur_usee_par_face(faces, usure):
    if not faces or usure is None:
        return None
    return usure / Decimal(faces)


def demontee_avant_usure(hauteur_finale):
    return hauteur_finale is not None and hauteur_finale > REGLAGES["seuil_non_finie_mm"]


def est_un_defaut(probleme, themes, hauteur_finale):
    """Meule cassée ou fissurée et pas finie : elle va dans la liste « Data défaut »."""
    return bool(probleme and THEME_DEFAUT in (themes or []) and demontee_avant_usure(hauteur_finale))


# --- Valeur inhabituelle -----------------------------------------------------------------------
def zone_habituelle(valeurs, coefficient=None):
    """Règle de Tukey : [Q1 - k × (Q3 - Q1) ; Q3 + k × (Q3 - Q1)], Q1 et Q3 = 25 % et 75 % des valeurs triées."""
    coefficient = REGLAGES["habitude_coefficient"] if coefficient is None else coefficient
    premier_quartile, _, troisieme_quartile = statistics.quantiles([float(valeur) for valeur in valeurs], n=4,
                                                                   method="inclusive")
    ecart = troisieme_quartile - premier_quartile
    return premier_quartile, troisieme_quartile, premier_quartile - coefficient * ecart, troisieme_quartile + coefficient * ecart


def avertissement_inhabituel(libelle, valeur, historique, portee, minimum):
    """Texte d'avertissement si la valeur sort de la zone habituelle de l'historique ; "" sinon."""
    historique = [valeur_passee for valeur_passee in historique if valeur_passee is not None]
    if valeur is None or len(historique) < minimum:
        return ""  # pas assez d'historique pour juger
    q1, q3, bas, haut = zone_habituelle(historique)
    if bas <= float(valeur) <= haut:
        return ""
    return (f"{libelle} : {valeur:g} est inhabituel (la plupart des valeurs de {portee} sont entre "
            f"{q1:g} et {q3:g}). Vérifiez la saisie.")


# Champs du montage comparés à toutes les saisies passées.
CHAMPS_HABITUELS_MONTAGE = [
    ("pression_arrosage", "Pression d'arrosage"),
    ("vitesse_rotation", "Vitesse de rotation"),
    ("vitesse_avance", "Vitesse d'avance"),
    ("hauteur_initiale", "Hauteur initiale de la meule"),
]


# --- Contrôles -----------------------------------------------------------------------------------
def controler_montage(machine, format_matiere, meule, date_montage, valeurs, commentaire, nouveaux_matricules=()):
    """Contrôles du montage. `valeurs` : les champs numériques (noms de CHAMPS_HABITUELS_MONTAGE)."""
    from .models import SaisieMeule

    erreurs, avertissements = [], []
    limites = [
        ("vitesse_rotation", "Vitesse de rotation", REGLAGES["vitesse_rotation_max"], "m/s"),
        ("vitesse_avance", "Vitesse d'avance", REGLAGES["vitesse_avance_max"], "mm/min"),
        ("hauteur_initiale", "Hauteur initiale de la meule", REGLAGES["hauteur_initiale_max"], "mm"),
    ]
    for champ, libelle, maximum, unite in limites:
        if valeurs.get(champ) is not None and valeurs[champ] > maximum:
            erreurs.append(f"{libelle} : {valeurs[champ]:g} dépasse le maximum de {maximum:g} {unite}.")

    machines_prevues = list(format_matiere.machines.all())
    if machines_prevues and machine not in machines_prevues:
        codes = " / ".join(machine_prevue.code for machine_prevue in machines_prevues)
        avertissements.append(f"Machine : {machine.code} n'est pas prévue pour {format_matiere} ({codes}).")
        if not commentaire.strip():
            erreurs.append(f"Commentaire obligatoire : {machine.code} n'est pas prévue pour {format_matiere}. Pourquoi ?")

    meules_prevues = list(format_matiere.meules.all())
    if meules_prevues and meule not in meules_prevues:
        references = " / ".join(meule_prevue.reference for meule_prevue in meules_prevues)
        avertissements.append(f"Meule : {meule.reference} n'est pas la meule prévue pour {format_matiere} ({references}).")

    if date_montage and date_montage > timezone.localdate():
        avertissements.append(f"Date de montage : le {date_montage:%d/%m/%Y} est dans le futur.")

    for numero in nouveaux_matricules:
        avertissements.append(f"Matricule {numero} : jamais utilisé, il sera ajouté à la liste. Vérifiez qu'il n'y a pas de faute de frappe.")

    historique = list(SaisieMeule.objects.values(*[champ for champ, _ in CHAMPS_HABITUELS_MONTAGE]))
    for champ, libelle in CHAMPS_HABITUELS_MONTAGE:
        valeur = valeurs.get(champ)
        valeurs_passees = [ligne[champ] for ligne in historique]
        if champ == "pression_arrosage":
            if valeur == 0:
                continue  # 0 = manomètre hors service : normal
            valeurs_passees = [valeur_passee for valeur_passee in valeurs_passees if valeur_passee != 0]
        texte = avertissement_inhabituel(libelle, valeur, valeurs_passees, "toutes les saisies",
                                         REGLAGES["habitude_minimum"])
        if texte:
            avertissements.append(texte)
    return erreurs, avertissements


def controler_demontage(saisie, compteur_fin, hauteur_finale, probleme, themes, commentaire, nouveaux_matricules=()):
    """Contrôles du démontage d'une saisie déjà montée."""
    from .models import SaisieMeule

    erreurs, avertissements = [], []
    if compteur_fin is not None and compteur_fin < saisie.compteur_debut:
        erreurs.append(f"Compteur au démontage : {compteur_fin} est inférieur au compteur au montage ({saisie.compteur_debut}).")
    if hauteur_finale is not None and hauteur_finale > saisie.hauteur_initiale:
        erreurs.append(f"Hauteur finale : {hauteur_finale:g} mm est supérieure à la hauteur initiale "
                       f"({saisie.hauteur_initiale:g} mm).")
    if demontee_avant_usure(hauteur_finale) and not commentaire.strip():
        erreurs.append(f"Commentaire obligatoire : la meule est démontée avant usure totale "
                       f"(il reste {hauteur_finale:g} mm). Pourquoi ?")
    if probleme and not themes:
        erreurs.append("Choisissez au moins un thème pour le problème signalé.")

    for numero in nouveaux_matricules:
        avertissements.append(f"Matricule {numero} : jamais utilisé, il sera ajouté à la liste. Vérifiez qu'il n'y a pas de faute de frappe.")

    autres = SaisieMeule.objects.demontees().exclude(pk=saisie.pk)
    meme_reference = autres.filter(meule=saisie.meule, format_matiere__matiere=saisie.format_matiere.matiere)
    portee = f"la meule {saisie.meule.reference} (matière {saisie.format_matiere.get_matiere_display().lower()})"
    texte = avertissement_inhabituel("Compteur au démontage", compteur_fin,
                                     list(meme_reference.values_list("compteur_fin", flat=True)), portee,
                                     min(REGLAGES["habitude_minimum"], REGLAGES["habitude_minimum_compteur"]))
    if texte:
        avertissements.append(texte)

    doublon = autres.filter(meule=saisie.meule, machine=saisie.machine, face=saisie.face,
                            date_montage=saisie.date_montage, compteur_fin=compteur_fin).first()
    if doublon and compteur_fin is not None:
        avertissements.append(
            f"Une saisie identique existe déjà (meule {saisie.meule.reference}, face {saisie.face}, machine "
            f"{saisie.machine.code}, montage du {saisie.date_montage:%d/%m/%Y}, compteur fin {compteur_fin}). "
            f"Est-ce un doublon ?")
    return erreurs, avertissements
