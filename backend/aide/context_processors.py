from .sujets import SUJET_DE_LA_PAGE


def aide(request):
    """Sujet du mode d'emploi qui explique la page affichée, pour le bouton « ? » de la barre du haut."""
    page_courante = request.resolver_match.url_name if request.resolver_match else None
    return {"sujet_aide_de_la_page": SUJET_DE_LA_PAGE.get(page_courante)}
