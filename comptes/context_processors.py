from . import roles


def profil(request):
    return {
        "profil": roles.profil(request.user),
        "peut_modifier": roles.peut_modifier(request.user),
        "peut_mouvementer": roles.peut_mouvementer(request.user),
    }
