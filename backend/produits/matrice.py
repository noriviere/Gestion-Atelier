"""Matrice produits × machines : état de chaque case et filtres de la page."""
import re
from .models import ProduitMachine

A_SECURISER = "a_securiser"
VIDE = ""

LIBELLES = {
    ProduitMachine.PROGRAMME: "Programmé",
    ProduitMachine.A_FAIRE: "À faire",
    A_SECURISER: "À sécuriser",
    ProduitMachine.NON_FAISABLE: "Non faisable",
    VIDE: "",
}

# Vues proposées au-dessus de la matrice : (code, libellé).
VUES = [
    ("", "Tous les produits"),
    ("non_securise", "Une seule machine programmée"),
    ("sans_machine", "Aucune machine programmée"),
    ("a_faire", "Avec une machine à faire ou à sécuriser"),
]


def cle_naturelle(texte):
    """Tri « naturel » des références : N2 avant N10, S8 avant S10."""
    return [int(morceau) if morceau.isdigit() else morceau.lower() for morceau in re.split(r"(\d+)", texte)]


def etat_affiche(etat, nombre_programmees):
    """« À faire » devient « à sécuriser » quand le produit tourne déjà sur une autre machine.

    « Possible, rien de prévu » s'affiche comme une case vide.
    """
    if etat == ProduitMachine.A_FAIRE and nombre_programmees > 0:
        return A_SECURISER
    if etat == ProduitMachine.POSSIBLE:
        return VIDE
    return etat


def vues_du_produit(etats_affiches):
    """Codes de VUES auxquels appartient un produit, d'après les états de sa ligne."""
    nombre_programmees = etats_affiches.count(ProduitMachine.PROGRAMME)
    vues = []
    if nombre_programmees == 1:
        vues.append("non_securise")
    if nombre_programmees == 0:
        vues.append("sans_machine")
    if ProduitMachine.A_FAIRE in etats_affiches or A_SECURISER in etats_affiches:
        vues.append("a_faire")
    return vues


def construire_matrice(produits, machines, fabrications):
    """Une ligne par produit, une case par machine, dans l'ordre des machines.

    Chaque case porte la fabrication (ou None) et l'état affiché ; chaque ligne, le nombre de machines
    programmées et les vues auxquelles elle appartient.
    """
    par_case = {(fabrication.produit_id, fabrication.machine_id): fabrication for fabrication in fabrications}
    lignes = []
    for produit in produits:
        fabrications_du_produit = [par_case.get((produit.pk, machine.pk)) for machine in machines]
        nombre_programmees = sum(
            1 for fabrication in fabrications_du_produit if fabrication and fabrication.etat == ProduitMachine.PROGRAMME
        )
        cases = []
        for machine, fabrication in zip(machines, fabrications_du_produit):
            etat = etat_affiche(fabrication.etat, nombre_programmees) if fabrication else VIDE
            cases.append({"machine": machine, "fabrication": fabrication, "etat": etat, "libelle": LIBELLES[etat]})
        etats = [case["etat"] for case in cases]
        lignes.append({
            "produit": produit,
            "cases": cases,
            "nombre_programmees": nombre_programmees,
            "vues": vues_du_produit(etats),
            "fiches": [case for case in cases if case["fabrication"] and case["fabrication"].a_une_fiche],
        })
    return lignes


def filtrer_lignes(lignes, recherche="", vue=""):
    recherche = recherche.strip().lower()
    selection = []
    for ligne in lignes:
        produit = ligne["produit"]
        textes = [produit.reference, produit.designation, produit.client]
        if recherche and not any(recherche in texte.lower() for texte in textes):
            continue
        if vue and vue not in ligne["vues"]:
            continue
        selection.append(ligne)
    return selection


def totaux(lignes):
    return {
        "produits": len(lignes),
        "programmees": sum(ligne["nombre_programmees"] for ligne in lignes),
        "non_securises": sum(1 for ligne in lignes if "non_securise" in ligne["vues"]),
        "sans_machine": sum(1 for ligne in lignes if "sans_machine" in ligne["vues"]),
        "a_faire": sum(1 for ligne in lignes for case in ligne["cases"]
                       if case["etat"] in (ProduitMachine.A_FAIRE, A_SECURISER)),
    }
