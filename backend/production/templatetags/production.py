from django import template

register = template.Library()


@register.filter
def pourcent(valeur):
    """Rapport (0,92) -> « 92 % » ; « — » quand il n'y a rien à afficher."""
    if valeur is None:
        return "—"
    return f"{round(float(valeur) * 100)} %"


@register.filter
def minutes(valeur):
    """450 -> « 7 h 30 » ; 45 -> « 45 min »."""
    valeur = int(valeur or 0)
    if valeur < 60:
        return f"{valeur} min"
    heures, reste = divmod(valeur, 60)
    return f"{heures} h {reste:02d}" if reste else f"{heures} h"
