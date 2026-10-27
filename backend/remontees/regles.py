"""Calculs, règles et contrôles des saisies meules, repris de l'application suivi-usure-meules.

Les règles (interrupteur et valeurs) se règlent dans le back-office ; leurs valeurs d'origine sont
celles du fichier config/champs.json de l'ancienne application. Les contrôles renvoient deux listes
de textes : les erreurs, qui bloquent l'enregistrement, et les avertissements, qui demandent
seulement une confirmation.
"""
import statistics
from collections import namedtuple
from decimal import Decimal

from django.utils import timezone

# « Nb faces/meule de 89 mm » : hauteur de référence de la durée de vie (fixe, comme dans le classeur).
HAUTEUR_REFERENCE_MM = 89
# Le compteur fin se compare aux saisies de la même meule et matière, souvent moins nombreuses.
MINIMUM_HISTORIQUE_COMPTEUR = 8

Parametre = namedtuple("Parametre", "cle libelle defaut mini maxi unite pas")
Regle = namedtuple("Regle", "code groupe titre aide interrupteur parametres")


def _parametre(cle, libelle, defaut, mini, maxi, unite="", pas="1"):
    return Parametre(cle, libelle, Decimal(defaut), Decimal(mini), Decimal(maxi), unite, pas)


# Le catalogue des règles, dans l'ordre du back-office. interrupteur=False : la règle est toujours active.
CATALOGUE = [
    Regle("non_finie", "Démontage", "Meule démontée avant usure totale",
          "Au-delà du seuil, la meule est marquée X. Interrupteur : exiger ou non une explication dans le commentaire.",
          True, [_parametre("seuil", "Seuil de hauteur finale", "2", "0", "30", "mm", "0.5")]),
    Regle("machine_non_prevue", "Démontage", "Machine non prévue pour ce format",
          "Actif : avertissement et commentaire obligatoire. Inactif : toute machine est acceptée sans question.",
          True, []),
    Regle("rotation_max", "Limites bloquantes", "Vitesse de rotation maximale", "Au-delà, la saisie est refusée.",
          True, [_parametre("valeur", "Maximum", "50", "1", "1000", "m/s")]),
    Regle("avance_max", "Limites bloquantes", "Vitesse d'avance maximale", "Au-delà, la saisie est refusée.",
          True, [_parametre("valeur", "Maximum", "1000", "1", "100000", "mm/min")]),
    Regle("hauteur_initiale_max", "Limites bloquantes", "Hauteur initiale maximale (meule neuve)",
          "Au-delà, la saisie est refusée.", True, [_parametre("valeur", "Maximum", "110", "1", "1000", "mm")]),
    Regle("hors_habitude", "Avertissements (non bloquants)", "Valeur inhabituelle par rapport à l'historique",
          "Pression, vitesses, hauteur initiale et compteur au démontage sont comparés aux saisies passées. "
          "Plus le coefficient est petit, plus on signale de valeurs.",
          True, [_parametre("coefficient", "Coefficient", "1.5", "0.5", "6", "", "0.1"),
                 _parametre("minimum", "Historique minimum", "20", "5", "500", "saisies")]),
    Regle("doublon", "Avertissements (non bloquants)", "Saisie identique à une saisie existante",
          "Même meule, machine, face, date de montage et compteur au démontage.", True, []),
    Regle("nouveau_matricule", "Avertissements (non bloquants)", "Matricule jamais utilisé",
          "Repère les fautes de frappe avant d'ajouter un matricule à la liste.", True, []),
    Regle("meule_non_prevue", "Avertissements (non bloquants)", "Meule différente de celle prévue pour le format",
          "Compare la meule saisie aux meules prévues dans la table « Formats et matière ».", True, []),
    Regle("date_futur", "Avertissements (non bloquants)", "Date de montage dans le futur", "", True, []),
    Regle("duree_eloignee", "Contrôle qualité (consultation)", "Durée de vie très éloignée des meules identiques",
          "Plus le coefficient est grand, moins de lignes sont signalées.",
          True, [_parametre("coefficient", "Coefficient", "3", "1", "10", "", "0.5")]),
    Regle("prix_meule", "Calculs", "Prix d'une meule moyenne",
          "Sert à estimer les euros perdus quand une meule n'est pas finie.",
          False, [_parametre("valeur", "Prix", "150", "1", "100000", "€")]),
]
PAR_CODE = {regle.code: regle for regle in CATALOGUE}


class Reglages:
    """Les règles telles que réglées dans le back-office, avec les valeurs d'origine pour le reste."""

    def __init__(self, enregistrees=None):
        self.enregistrees = enregistrees or {}  # {code: (actif, {cle: texte})}

    def actif(self, code):
        regle = PAR_CODE[code]
        return not regle.interrupteur or self.enregistrees.get(code, (True, {}))[0]

    def valeur(self, code, cle="valeur"):
        parametre = next(parametre for parametre in PAR_CODE[code].parametres if parametre.cle == cle)
        texte = self.enregistrees.get(code, (True, {}))[1].get(cle)
        return parametre.defaut if texte is None else Decimal(texte)

    @property
    def seuil_non_finie(self):
        return self.valeur("non_finie", "seuil")


def lire_reglages():
    from .models import RegleMeule

    return Reglages({regle.code: (regle.actif, regle.valeurs) for regle in RegleMeule.objects.all()})


DEFAUTS = Reglages()

THEME_DEFAUT = "Meule cassée ou fissurée"
# Thèmes proposés au démontage avant tout réglage (le back-office les modifie).
THEMES_D_ORIGINE = [
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
    return None if faces_mm is None else faces_mm * HAUTEUR_REFERENCE_MM


def hauteur_usee_par_face(faces, usure):
    if not faces or usure is None:
        return None
    return usure / Decimal(faces)


def demontee_avant_usure(hauteur_finale, reglages=DEFAUTS):
    return hauteur_finale is not None and hauteur_finale > reglages.seuil_non_finie


def est_un_defaut(probleme, themes, hauteur_finale, reglages=DEFAUTS):
    """Meule cassée ou fissurée et pas finie : elle va dans la liste « Data défaut »."""
    return bool(probleme and THEME_DEFAUT in (themes or []) and demontee_avant_usure(hauteur_finale, reglages))


def perte_estimee(hauteur_initiale, hauteur_finale, prix):
    """Valeur de la meule pas utilisée : hauteur restante / hauteur initiale × prix d'une meule moyenne."""
    if not hauteur_initiale or not hauteur_finale or hauteur_initiale <= 0 or hauteur_finale <= 0:
        return Decimal(0)
    return min(hauteur_finale, hauteur_initiale) / hauteur_initiale * prix


# --- Valeur inhabituelle -----------------------------------------------------------------------
def zone_habituelle(valeurs, coefficient):
    """Règle de Tukey : [Q1 - k × (Q3 - Q1) ; Q3 + k × (Q3 - Q1)], Q1 et Q3 = 25 % et 75 % des valeurs triées."""
    premier_quartile, _, troisieme_quartile = statistics.quantiles([float(valeur) for valeur in valeurs], n=4,
                                                                   method="inclusive")
    ecart = troisieme_quartile - premier_quartile
    coefficient = float(coefficient)
    return premier_quartile, troisieme_quartile, premier_quartile - coefficient * ecart, troisieme_quartile + coefficient * ecart


def avertissement_inhabituel(libelle, valeur, historique, portee, minimum, coefficient):
    """Texte d'avertissement si la valeur sort de la zone habituelle de l'historique ; "" sinon."""
    historique = [valeur_passee for valeur_passee in historique if valeur_passee is not None]
    if valeur is None or len(historique) < minimum:
        return ""  # pas assez d'historique pour juger
    q1, q3, bas, haut = zone_habituelle(historique, coefficient)
    if bas <= float(valeur) <= haut:
        return ""
    return (f"{libelle} : {valeur:g} est inhabituel (la plupart des valeurs de {portee} sont entre "
            f"{q1:g} et {q3:g}). Vérifiez la saisie.")


def avertissement_nouveau_matricule(numero):
    return f"Matricule {numero} : jamais utilisé, il sera ajouté à la liste. Vérifiez qu'il n'y a pas de faute de frappe."


# Champs du montage comparés à toutes les saisies passées.
CHAMPS_HABITUELS_MONTAGE = [
    ("pression_arrosage", "Pression d'arrosage"),
    ("vitesse_rotation", "Vitesse de rotation"),
    ("vitesse_avance", "Vitesse d'avance"),
    ("hauteur_initiale", "Hauteur initiale de la meule"),
]
# Limites bloquantes : règle, champ, libellé, unité.
LIMITES = [
    ("rotation_max", "vitesse_rotation", "Vitesse de rotation", "m/s"),
    ("avance_max", "vitesse_avance", "Vitesse d'avance", "mm/min"),
    ("hauteur_initiale_max", "hauteur_initiale", "Hauteur initiale de la meule", "mm"),
]


# --- Contrôles en direct (dans le navigateur, avant l'enregistrement) --------------------------------
def _zone(valeurs, minimum, coefficient):
    """Zone habituelle à envoyer au navigateur ; None s'il n'y a pas assez d'historique pour juger."""
    valeurs = [valeur for valeur in valeurs if valeur is not None]
    if len(valeurs) < minimum:
        return None
    q1, q3, bas, haut = zone_habituelle(valeurs, coefficient)
    return {"q1": q1, "q3": q3, "bas": bas, "haut": haut}


def controles_en_direct(reglages, saisie=None):
    """Ce que remontees.js doit savoir pour afficher les erreurs et avertissements sous les champs, pendant la saisie.

    Les mêmes règles sont refaites par le serveur à l'enregistrement : le navigateur ne fait que prévenir plus tôt."""
    from .models import Matricule, SaisieMeule

    donnees = {
        "actives": {regle.code: reglages.actif(regle.code) for regle in CATALOGUE},
        "limites": {champ: {"maximum": float(reglages.valeur(code)), "unite": unite}
                    for code, champ, _, unite in LIMITES if reglages.actif(code)},
        "seuil_non_finie": float(reglages.seuil_non_finie),
        "prix_meule": float(reglages.valeur("prix_meule")),
        "matricules": list(Matricule.objects.values_list("numero", flat=True)),
        "theme_defaut": THEME_DEFAUT,
        "zones": {},
    }
    minimum = int(reglages.valeur("hors_habitude", "minimum"))
    coefficient = reglages.valeur("hors_habitude", "coefficient")
    if saisie is None:
        if reglages.actif("hors_habitude"):
            historique = list(SaisieMeule.objects.values(*[champ for champ, _ in CHAMPS_HABITUELS_MONTAGE]))
            for champ, _ in CHAMPS_HABITUELS_MONTAGE:
                valeurs = [ligne[champ] for ligne in historique]
                if champ == "pression_arrosage":
                    valeurs = [valeur for valeur in valeurs if valeur != 0]  # 0 = manomètre hors service
                donnees["zones"][champ] = _zone(valeurs, minimum, coefficient)
        # Médianes attendues : une ligne par meule démontée (meule, machine, matière, face, faces pour 89 mm).
        donnees["durees"] = [
            [ligne.meule_id, ligne.machine_id, ligne.format_matiere.matiere, ligne.face, round(float(duree), 1)]
            for ligne in SaisieMeule.objects.demontees().select_related("format_matiere")
            for duree in [ligne.faces_par_meule_reference] if duree is not None and ligne.nombre_faces_brut
        ]
    else:
        if reglages.actif("hors_habitude"):
            meme_reference = (SaisieMeule.objects.demontees().exclude(pk=saisie.pk)
                              .filter(meule=saisie.meule, format_matiere__matiere=saisie.format_matiere.matiere))
            donnees["zones"]["compteur_fin"] = _zone(list(meme_reference.values_list("compteur_fin", flat=True)),
                                                     min(minimum, MINIMUM_HISTORIQUE_COMPTEUR), coefficient)
        donnees["saisie"] = {"compteur_debut": saisie.compteur_debut, "hauteur_initiale": float(saisie.hauteur_initiale),
                             "meule": saisie.meule.reference}
        donnees["perte_annee"] = float(sum(
            (perte_estimee(hi, hf, reglages.valeur("prix_meule")) for hi, hf in SaisieMeule.objects.demontees()
             .filter(date_montage__year=timezone.localdate().year).values_list("hauteur_initiale", "hauteur_finale")),
            Decimal(0)))
        donnees["annee"] = timezone.localdate().year
    return donnees


# --- Contrôles -----------------------------------------------------------------------------------
def controler_montage(machine, format_matiere, meule, date_montage, valeurs, commentaire, nouveaux_matricules=(),
                      reglages=None):
    """Contrôles du montage. `valeurs` : les champs numériques (noms de CHAMPS_HABITUELS_MONTAGE)."""
    from .models import SaisieMeule

    reglages = reglages or lire_reglages()
    erreurs, avertissements = [], []
    for code, champ, libelle, unite in LIMITES:
        maximum = reglages.valeur(code)
        if reglages.actif(code) and valeurs.get(champ) is not None and valeurs[champ] > maximum:
            erreurs.append(f"{libelle} : {valeurs[champ]:g} dépasse le maximum de {maximum:g} {unite}.")

    machines_prevues = list(format_matiere.machines.all())
    if reglages.actif("machine_non_prevue") and machines_prevues and machine not in machines_prevues:
        codes = " / ".join(machine_prevue.code for machine_prevue in machines_prevues)
        avertissements.append(f"Machine : {machine.code} n'est pas prévue pour {format_matiere} ({codes}).")
        if not commentaire.strip():
            erreurs.append(f"Commentaire obligatoire : {machine.code} n'est pas prévue pour {format_matiere}. Pourquoi ?")

    meules_prevues = list(format_matiere.meules.all())
    if reglages.actif("meule_non_prevue") and meules_prevues and meule not in meules_prevues:
        references = " / ".join(meule_prevue.reference for meule_prevue in meules_prevues)
        avertissements.append(f"Meule : {meule.reference} n'est pas la meule prévue pour {format_matiere} ({references}).")

    if reglages.actif("date_futur") and date_montage and date_montage > timezone.localdate():
        avertissements.append(f"Date de montage : le {date_montage:%d/%m/%Y} est dans le futur.")

    if reglages.actif("nouveau_matricule"):
        avertissements += [avertissement_nouveau_matricule(numero) for numero in nouveaux_matricules]

    if reglages.actif("hors_habitude"):
        historique = list(SaisieMeule.objects.values(*[champ for champ, _ in CHAMPS_HABITUELS_MONTAGE]))
        for champ, libelle in CHAMPS_HABITUELS_MONTAGE:
            valeur = valeurs.get(champ)
            valeurs_passees = [ligne[champ] for ligne in historique]
            if champ == "pression_arrosage":
                if valeur == 0:
                    continue  # 0 = manomètre hors service : normal
                valeurs_passees = [valeur_passee for valeur_passee in valeurs_passees if valeur_passee != 0]
            texte = avertissement_inhabituel(libelle, valeur, valeurs_passees, "toutes les saisies",
                                             reglages.valeur("hors_habitude", "minimum"),
                                             reglages.valeur("hors_habitude", "coefficient"))
            if texte:
                avertissements.append(texte)
    return erreurs, avertissements


def controler_demontage(saisie, compteur_fin, hauteur_finale, probleme, themes, commentaire, nouveaux_matricules=(),
                        reglages=None):
    """Contrôles du démontage d'une saisie déjà montée."""
    from .models import SaisieMeule

    reglages = reglages or lire_reglages()
    erreurs, avertissements = [], []
    if compteur_fin is not None and compteur_fin < saisie.compteur_debut:
        erreurs.append(f"Compteur au démontage : {compteur_fin} est inférieur au compteur au montage ({saisie.compteur_debut}).")
    if hauteur_finale is not None and hauteur_finale > saisie.hauteur_initiale:
        erreurs.append(f"Hauteur finale : {hauteur_finale:g} mm est supérieure à la hauteur initiale "
                       f"({saisie.hauteur_initiale:g} mm).")
    if reglages.actif("non_finie") and demontee_avant_usure(hauteur_finale, reglages) and not commentaire.strip():
        erreurs.append(f"Commentaire obligatoire : la meule est démontée avant usure totale "
                       f"(il reste {hauteur_finale:g} mm). Pourquoi ?")
    if probleme and not themes and not commentaire.strip():
        erreurs.append("Choisissez un thème ou décrivez le problème dans le commentaire.")

    if reglages.actif("nouveau_matricule"):
        avertissements += [avertissement_nouveau_matricule(numero) for numero in nouveaux_matricules]

    autres = SaisieMeule.objects.demontees().exclude(pk=saisie.pk)
    if reglages.actif("hors_habitude"):
        meme_reference = autres.filter(meule=saisie.meule, format_matiere__matiere=saisie.format_matiere.matiere)
        portee = f"la meule {saisie.meule.reference} (matière {saisie.format_matiere.get_matiere_display().lower()})"
        texte = avertissement_inhabituel("Compteur au démontage", compteur_fin,
                                         list(meme_reference.values_list("compteur_fin", flat=True)), portee,
                                         min(reglages.valeur("hors_habitude", "minimum"), MINIMUM_HISTORIQUE_COMPTEUR),
                                         reglages.valeur("hors_habitude", "coefficient"))
        if texte:
            avertissements.append(texte)

    if reglages.actif("doublon") and compteur_fin is not None:
        doublon = autres.filter(meule=saisie.meule, machine=saisie.machine, face=saisie.face,
                                date_montage=saisie.date_montage, compteur_fin=compteur_fin).exists()
        if doublon:
            avertissements.append(
                f"Une saisie identique existe déjà (meule {saisie.meule.reference}, face {saisie.face}, machine "
                f"{saisie.machine.code}, montage du {saisie.date_montage:%d/%m/%Y}, compteur fin {compteur_fin}). "
                f"Est-ce un doublon ?")
    return erreurs, avertissements
