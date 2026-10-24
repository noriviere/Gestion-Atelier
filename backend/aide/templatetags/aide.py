from django import template
from django.urls import reverse
from django.utils.html import format_html

from comptes.droits import BLOCS, FONCTIONS

from ..sujets import PAR_CODE

register = template.Library()

BLOC_DE_LA_FONCTION = {fonction.code: bloc for bloc in BLOCS for fonction in bloc.fonctions}


@register.simple_tag
def info(code_sujet, ancre, libelle):
    """Petit « i » qui ouvre le mode d'emploi à l'explication d'une case ou d'un bouton.

    Exemple : {% info "stock" "stock-mini" "Stock mini" %}
    """
    if code_sujet not in PAR_CODE:
        raise template.TemplateSyntaxError(f"Sujet d'aide inconnu : {code_sujet}")
    adresse = reverse("aide_sujet", args=[code_sujet]) + "#" + ancre
    return format_html(
        '<a class="info" href="{}" title="Aide : {}" aria-label="Aide : {}" data-info>i</a>', adresse, libelle, libelle
    )


@register.simple_tag(takes_context=True)
def droit_requis(context, *codes):
    """Dans le mode d'emploi : le droit nécessaire, et si le profil de la personne qui lit l'a."""
    for code in codes:
        if code not in FONCTIONS:
            raise template.TemplateSyntaxError(f"Droit inconnu : {code}")
    droits_du_lecteur = context.get("droits", {})
    libelles = " ou ".join(f"« {FONCTIONS[code].libelle} »" for code in codes)
    blocs = sorted({BLOC_DE_LA_FONCTION[code].libelle for code in codes})
    if any(droits_du_lecteur.get(code) for code in codes):
        etiquette = format_html('<span class="etiquette ok">votre profil l\'a</span>')
    else:
        etiquette = format_html('<span class="etiquette">pas avec votre profil</span>')
    return format_html(
        '<p class="droit-requis">Droit nécessaire : {} (bloc {}) {}</p>', libelles, ", ".join(blocs), etiquette
    )
