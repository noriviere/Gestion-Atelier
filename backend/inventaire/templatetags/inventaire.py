from django import template

from inventaire.calculs import formater_ecart

register = template.Library()


@register.filter
def signe(ecart):
    """Écart avec son signe : +2, −1,5, 0."""
    return formater_ecart(ecart) if ecart is not None else ""


@register.filter
def euros_signes(valeur):
    """Valeur d'un écart avec son signe et deux décimales : −36,00 €."""
    if valeur is None:
        return ""
    signe_valeur = "+" if valeur > 0 else "−" if valeur < 0 else ""
    return f"{signe_valeur}{abs(valeur):.2f} €".replace(".", ",")
