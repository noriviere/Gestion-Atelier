"""Statistiques et contrôle qualité des meules démontées, repris de la page de consultation de suivi-usure-meules.

Les fonctions reçoivent la liste des saisies démontées (lue une fois par la vue) et ne font pas de requête.
"""
import statistics
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from . import regles

GRAVE, VERIF, MINEUR = "probable erreur", "à vérifier", "mineur"
GRAVITES = [GRAVE, VERIF, MINEUR]
# Moins de cas : la médiane est donnée mais signalée comme peu fiable, et on élargit le critère.
MINIMUM_FIABLE = 5
# Une durée de vie n'est jugée « éloignée » que dans un groupe d'au moins autant de meules identiques.
MINIMUM_GROUPE_ELOIGNE = 8
DATE_TRES_ANCIENNE = timezone.datetime(2015, 1, 1).date()


def _mediane(valeurs):
    return round(statistics.median(valeurs)) if valeurs else None


def duree_de_vie(saisie):
    """Faces pour une meule de 89 mm, en nombre décimal ; None si elle ne se calcule pas.

    Une saisie sans face ou au compteur à l'envers est une erreur (signalée à part) : elle ne compte pas."""
    if not saisie.nombre_faces_brut or saisie.nombre_faces_brut < 0:
        return None
    valeur = saisie.faces_par_meule_reference
    return None if valeur is None else float(valeur)


def mediane_attendue(saisies, meule, machine, matiere, face):
    """Médiane des faces par meule de 89 mm pour une meule : on part du critère le plus précis,
    et on élargit tant qu'il y a moins de MINIMUM_FIABLE cas. Renvoie (médiane, nombre de cas, critère, fiable)."""
    niveaux = [
        ("meule + machine + matière", lambda saisie: saisie.machine_id == machine.pk and saisie.format_matiere.matiere == matiere),
        ("meule + matière", lambda saisie: saisie.format_matiere.matiere == matiere),
        ("meule seule", lambda saisie: True),
    ]
    repli = None
    for critere, garder in niveaux:
        valeurs = [duree_de_vie(saisie) for saisie in saisies
                   if saisie.meule_id == meule.pk and saisie.face == face and garder(saisie)
                   and duree_de_vie(saisie) is not None]
        if not valeurs:
            continue
        resultat = {"mediane": _mediane(valeurs), "nombre": len(valeurs), "critere": critere,
                    "fiable": len(valeurs) >= MINIMUM_FIABLE}
        if resultat["fiable"]:
            return resultat
        repli = repli or resultat
    return repli


def medianes_par_reference(saisies):
    """Une ligne par meule et matière : médiane et nombre de cas pour la face A, la face B et les deux."""
    groupes = defaultdict(lambda: {"A": [], "B": []})
    for saisie in saisies:
        valeur = duree_de_vie(saisie)
        if valeur is not None:
            groupes[(saisie.meule.reference, saisie.format_matiere.get_matiere_display())][saisie.face].append(valeur)
    lignes = []
    for (reference, matiere), par_face in sorted(groupes.items()):
        toutes = par_face["A"] + par_face["B"]
        lignes.append({
            "meule": reference, "matiere": matiere,
            "face_a": _mediane(par_face["A"]), "nombre_a": len(par_face["A"]),
            "face_b": _mediane(par_face["B"]), "nombre_b": len(par_face["B"]),
            "toutes": _mediane(toutes), "nombre": len(toutes), "mini": round(min(toutes)), "maxi": round(max(toutes)),
        })
    return lignes


def derniers_mois(nombre, aujourdhui=None):
    """Les `nombre` derniers mois (année, mois), du plus ancien au mois en cours."""
    aujourdhui = aujourdhui or timezone.localdate()
    annee, mois = aujourdhui.year, aujourdhui.month
    resultat = []
    for _ in range(nombre):
        resultat.append((annee, mois))
        annee, mois = (annee, mois - 1) if mois > 1 else (annee - 1, 12)
    return list(reversed(resultat))


def evolution_par_mois(saisies, mois):
    """Médiane par meule et matière, mois par mois (mois de montage). Une case vide quand aucune meule n'a été montée."""
    groupes = defaultdict(lambda: defaultdict(list))
    for saisie in saisies:
        valeur = duree_de_vie(saisie)
        if valeur is not None:
            cle = (saisie.meule.reference, saisie.format_matiere.get_matiere_display())
            groupes[cle][(saisie.date_montage.year, saisie.date_montage.month)].append(valeur)
    return [{"meule": reference, "matiere": matiere,
             "medianes": [_mediane(par_mois.get(un_mois, [])) for un_mois in mois]}
            for (reference, matiere), par_mois in sorted(groupes.items())]


def perte(saisies, annee, prix):
    """Euros de meule pas utilisée sur les meules montées dans l'année : total, nombre de meules, détail par machine."""
    total, nombre, par_machine = Decimal(0), 0, defaultdict(Decimal)
    for saisie in saisies:
        if saisie.date_montage.year != annee:
            continue
        valeur = regles.perte_estimee(saisie.hauteur_initiale, saisie.hauteur_finale, prix)
        if valeur:
            total += valeur
            nombre += 1
            par_machine[saisie.machine.code] += valeur
    return {"annee": annee, "total": total, "nombre": nombre, "prix": prix,
            "par_machine": sorted(par_machine.items(), key=lambda element: -element[1])}


def anomalies(saisies, reglages):
    """Lignes qui semblent absurdes, à vérifier. Ne modifie rien : produit seulement une liste.

    Chaque anomalie : {"saisie", "champ", "valeur", "motif", "gravite"}, triées de la plus grave à la moins grave."""
    resultat = []

    def ajouter(saisie, champ, valeur, motif, gravite):
        resultat.append({"saisie": saisie, "champ": champ, "valeur": "" if valeur is None else str(valeur),
                         "motif": motif, "gravite": gravite})

    aujourdhui = timezone.localdate()
    for saisie in saisies:
        # Limites (une saisie reprise de l'historique ou faite avant un changement de règle peut les dépasser).
        for code, champ, libelle, unite in regles.LIMITES:
            valeur, maximum = getattr(saisie, champ), reglages.valeur(code)
            if reglages.actif(code) and valeur is not None and valeur > maximum:
                ajouter(saisie, libelle, valeur, f"supérieur à {maximum:g} {unite}", GRAVE)
        if saisie.compteur_fin is not None and saisie.compteur_fin < saisie.compteur_debut:
            ajouter(saisie, "Compteur au démontage", saisie.compteur_fin,
                    f"inférieur au compteur au montage ({saisie.compteur_debut})", GRAVE)
        elif saisie.nombre_faces_brut == 0:
            ajouter(saisie, "Compteur au démontage", saisie.compteur_fin, "aucune face (égal au compteur au montage)", VERIF)
        if saisie.hauteur_finale is not None and saisie.hauteur_finale > saisie.hauteur_initiale:
            ajouter(saisie, "Hauteur finale", saisie.hauteur_finale,
                    f"supérieure à la hauteur initiale ({saisie.hauteur_initiale:g})", GRAVE)
        if saisie.date_montage > aujourdhui:
            ajouter(saisie, "Date de montage", f"{saisie.date_montage:%d/%m/%Y}", "date dans le futur", GRAVE)
        elif saisie.date_montage < DATE_TRES_ANCIENNE:
            ajouter(saisie, "Date de montage", f"{saisie.date_montage:%d/%m/%Y}", "date très ancienne", VERIF)
        machines_prevues = saisie.format_matiere.machines.all()
        if machines_prevues and saisie.machine not in machines_prevues:
            ajouter(saisie, "Machine", saisie.machine.code, f"pas prévue pour {saisie.format_matiere}", VERIF)
        meules_prevues = saisie.format_matiere.meules.all()
        if meules_prevues and saisie.meule not in meules_prevues:
            ajouter(saisie, "Meule", saisie.meule.reference, f"pas prévue pour {saisie.format_matiere}", VERIF)
        if saisie.non_finie and not saisie.commentaire.strip():
            ajouter(saisie, "Commentaire", "", "meule non finie sans explication", MINEUR)

    # Durée de vie très éloignée des autres meules identiques (même meule et même matière).
    if reglages.actif("duree_eloignee"):
        coefficient = reglages.valeur("duree_eloignee", "coefficient")
        groupes = defaultdict(list)
        for saisie in saisies:
            valeur = duree_de_vie(saisie)
            if valeur is not None:
                groupes[(saisie.meule_id, saisie.format_matiere.matiere)].append((saisie, valeur))
        for groupe in groupes.values():
            if len(groupe) < MINIMUM_GROUPE_ELOIGNE:
                continue
            q1, q3, bas, haut = regles.zone_habituelle([valeur for _, valeur in groupe], coefficient)
            for saisie, valeur in groupe:
                if not bas <= valeur <= haut:
                    ajouter(saisie, "Faces pour une meule de 89 mm", round(valeur),
                            f"très éloigné des autres meules identiques (la plupart entre {q1:.0f} et {q3:.0f})", VERIF)

    # Doublons : même meule, machine, face, date de montage et compteur au démontage.
    deja_vues = {}
    for saisie in sorted(saisies, key=lambda saisie: saisie.pk):
        cle = (saisie.meule_id, saisie.machine_id, saisie.face, saisie.date_montage, saisie.compteur_fin)
        if cle in deja_vues:
            ajouter(saisie, "Saisie", "", f"identique à la saisie n° {deja_vues[cle]} (doublon ?)", VERIF)
        else:
            deja_vues[cle] = saisie.pk

    resultat.sort(key=lambda anomalie: (GRAVITES.index(anomalie["gravite"]), -anomalie["saisie"].pk))
    return resultat
