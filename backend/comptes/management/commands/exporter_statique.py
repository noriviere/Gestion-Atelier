"""Exporte la démo en pages HTML statiques, publiables sur GitHub Pages.

Le site est parcouru avec chaque compte de démonstration ; chaque profil obtient
son propre jeu de pages, et une page d'accueil permet de choisir le profil.
Les liens sont rendus relatifs, les liens vers l'administration ouvrent un message
de démo, et les saisies sont simulées par static/demo.js. Les documents et photos des fiches
sont copiés tels quels à côté des pages.
"""
import posixpath
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.test import Client, override_settings

PROFILS = [
    # dossier, compte, titre, description
    ("admin", "admin", "Admin", "Tous les droits, dont la page Droits qui règle ceux des autres profils."),
    ("methode", "methode", "Méthode et management",
     "Crée et modifie articles, outils, produits et seuils ; consulte tout."),
    ("intendant", "intendante", "Intendant",
     "Gère les commandes, les articles, les fournisseurs et les comptages d'inventaire ; consulte tout."),
    ("regleur", "regleur", "Régleur",
     "Consulte les fiches avec photos et documents, ajuste les réglages, saisit les sorties de stock."),
    ("operateur", "operateur", "Opérateur",
     "Consulte les fiches et saisit les sorties de stock."),
]

# Formulaires de consultation (méthode GET) : leur page est exportée et le formulaire y mène.
# Les autres formulaires envoient des saisies, simulées par demo.js.
FORMULAIRES_DE_CONSULTATION = ("/recherche/",)
# data-url-… : adresses lues par le JavaScript des pages (matrice produits × machines), réécrites mais pas parcourues.
LIEN = re.compile(r'(href|src|action|data-url-[a-z-]+)="(/[^"]*)"')


def chemin_statique(url):
    """/articles/?alerte=1 -> articles/alerte-1/index.html (chemin relatif au dossier du profil).

    Un fichier (dernier segment avec une extension, ex. /produits/documents/3/plan.pdf) garde son chemin.
    """
    parties = urlsplit(url)
    chemin = parties.path.strip("/")
    if "." in posixpath.basename(chemin) and not parties.query:
        return chemin
    for cle, valeur in parse_qsl(parties.query):
        chemin = posixpath.join(chemin, re.sub(r"[^\w-]", "_", f"{cle}-{valeur}"))
    return posixpath.join(chemin, "index.html") if chemin else "index.html"


class Command(BaseCommand):
    help = "Exporte la démo en site statique (par défaut dans le dossier site/)."

    def add_arguments(self, parser):
        parser.add_argument("--sortie", default="site")

    @override_settings(DEMO_STATIQUE=True, ALLOWED_HOSTS=["*"], DEBUG=False)
    def handle(self, *args, **options):
        sortie = Path(options["sortie"])
        if sortie.exists():
            # Le dossier est effacé avant l'export : seulement s'il est vide ou contient un export précédent.
            if any(sortie.iterdir()) and not (sortie / "index.html").exists():
                raise CommandError(f"{sortie} n'est pas vide et ne ressemble pas à un export : choisissez un autre --sortie.")
            shutil.rmtree(sortie)
        sortie.mkdir(parents=True)
        shutil.copytree(settings.FRONTEND_DIR / "static", sortie / "static")
        (sortie / ".nojekyll").write_text("")

        for dossier, compte, titre, _ in PROFILS:
            client = Client()
            client.force_login(User.objects.get(username=compte))
            nb = self.parcourir(client, sortie, dossier)
            self.stdout.write(f"{titre} : {nb} pages")

        (sortie / "index.html").write_text(self.page_profils(), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Site statique écrit dans {sortie}/"))

    def parcourir(self, client, sortie, dossier):
        a_voir, vues = ["/"], set()
        while a_voir:
            url = a_voir.pop()
            if url in vues:
                continue
            vues.add(url)
            reponse = client.get(url)
            if reponse.status_code != 200:
                self.stderr.write(f"{dossier}{url} : {reponse.status_code}")
                continue
            fichier = posixpath.join(dossier, chemin_statique(url))
            cible = sortie / fichier
            cible.parent.mkdir(parents=True, exist_ok=True)
            if not reponse.get("Content-Type", "").startswith("text/html"):
                cible.write_bytes(b"".join(reponse.streaming_content) if reponse.streaming else reponse.content)
                continue
            html = reponse.content.decode()
            for attribut, lien in LIEN.findall(html):
                # Les formulaires envoient des saisies : leur adresse n'est pas une page à exporter,
                # sauf pour les formulaires de consultation.
                a_parcourir = attribut in ("href", "src") or (attribut == "action" and lien in FORMULAIRES_DE_CONSULTATION)
                page = lien.split("#")[0]  # /aide/stock/#stock-mini : la page est /aide/stock/
                if a_parcourir and self.est_page(page) and page not in vues:
                    a_voir.append(page)
            cible.write_text(self.reecrire(html, fichier, dossier), encoding="utf-8")
        return len(vues)

    @staticmethod
    def est_page(lien):
        return not lien.startswith(("/admin", "/static", "/deconnexion", "/connexion", "/__"))

    def reecrire(self, html, fichier, dossier):
        repertoire = posixpath.dirname(fichier)

        def relatif(cible):
            return posixpath.relpath(cible, repertoire) if repertoire else cible

        def remplacer(correspondance):
            attribut, lien = correspondance.groups()
            if lien.startswith("/admin"):
                return f'{attribut}="#" data-demo-parametrage'
            if lien.startswith("/__profils__"):
                return f'{attribut}="{relatif("index.html")}"'
            if lien.startswith(settings.STATIC_URL if settings.STATIC_URL.startswith("/") else "/" + settings.STATIC_URL):
                return f'{attribut}="{relatif(lien.lstrip("/"))}"'
            if not self.est_page(lien) or (attribut == "action" and lien not in FORMULAIRES_DE_CONSULTATION):
                return f'{attribut}="#"'
            page, diese, ancre = lien.partition("#")
            return f'{attribut}="{relatif(posixpath.join(dossier, chemin_statique(page)))}{diese}{ancre}"'

        return LIEN.sub(remplacer, html)

    def page_profils(self):
        profils = [{"dossier": dossier, "titre": titre, "description": description}
                   for dossier, _, titre, description in PROFILS]
        return render_to_string("profils_demo.html", {"profils": profils})
