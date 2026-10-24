# Gestion Atelier

Application web de gestion des données d'atelier : stock de pièces d'usure et de consommables,
arborescence d'outillage, fiches produit par machine, avec trois niveaux d'accès.

Cette version est une **démo** avec des données fictives, destinée à présenter le projet.

## Ce que montre la démo

- **Stock** : articles avec type d'inventaire, emplacement, stock mini et quantité mini de commande,
  plusieurs fournisseurs dont un préféré, sorties et entrées de stock.
- **À commander** : articles sous le stock mini, regroupés par fournisseur préféré, imprimable.
- **Inventaires tournants** : fréquence de comptage par article, feuille de comptage imprimable
  par type d'inventaire, saisie des quantités comptées qui corrige le stock.
- **Outillage** : arborescence outil, sous-ensembles et pièces d'usure, avec leur stock.
  Le profil Méthode crée et modifie les outils et leurs pièces directement dans l'application ;
  depuis la fiche d'un outil, tous les profils sortent du stock une pièce remplacée.
- **Produits** : un produit par machine avec cadence, outillages, consommables et notes,
  affiché sous forme de fiche imprimable.
- **Profils** : `Admin`, `Méthode et management` (paramétrage via le menu Paramétrage),
  `Régleur et opérateur` (consultation, mouvements de stock, comptages).

Comptes de démonstration, tous avec le mot de passe `demo` :
`admin`, `methode`, `chef`, `regleur`, `intendante`, `operateur`.

## Démo en ligne

Une version statique de la démo est publiée sur GitHub Pages :
https://noriviere.github.io/Gestion-Atelier/

On y choisit un profil (Admin, Méthode et management, Régleur et opérateur) pour voir l'application
avec ses droits. Les sorties de stock (depuis un article ou une fiche outil), entrées, comptages
et filtres sont simulés dans le navigateur : les stocks et mouvements saisis sont gardés dans ce
navigateur et repris sur toutes les pages, jusqu'au bouton « Remettre à zéro ». La création et la
modification d'outils sont vérifiées puis confirmées, sans être conservées. Rien n'est envoyé. Le site est régénéré automatiquement à chaque modification de `main`
(workflow `.github/workflows/pages.yml`, commande `python manage.py exporter_statique`).

## Lancer la démo sur un PC (Python 3.11 ou plus)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py charger_demo
python manage.py runserver 0.0.0.0:8000
```

Puis ouvrir http://localhost:8000 (ou l'adresse du PC depuis un autre poste du réseau).

## Lancer sur la machine virtuelle Linux (Docker)

```bash
docker compose up -d --build
docker compose exec web python manage.py charger_demo
```

L'application répond sur le port 8000, avec une base PostgreSQL.

## Modifier les données fictives

Toutes les données de la démo sont dans [`demo/donnees.py`](demo/donnees.py), sous forme de listes
simples. Après modification, `python manage.py charger_demo` efface et recharge tout.

## Règles de calcul

- Un article est **à commander** quand son stock est inférieur ou égal au stock mini.
- La **quantité suggérée** ramène le stock au niveau du mini, plus le mini de commande :
  `max(mini de commande, stock mini − stock + mini de commande)`.
- Un article est **à inventorier** quand son dernier comptage date de plus que sa fréquence.

## Tests

```bash
python manage.py test
```

Les tests sont dans `backend/tests/` : règles de stock et d'inventaire, outillage et fiches produit,
profils et droits, pages et export statique.

## Organisation du code

```
backend/                 Code Python (Django)
  config/                Réglages, adresses, lanceur de tests
  comptes/               Profils d'accès, connexion obligatoire, commandes charger_demo et exporter_statique
  inventaire/            Fournisseurs, articles, mouvements, inventaires
  outillage/             Outils, sous-ensembles et pièces montées
  produits/              Machines, produits, fiches produit sur machine
  demo/                  Données fictives de la démo
  tests/                 Tests unitaires
frontend/                Interface
  templates/             Gabarits HTML, un dossier par module
  static/css/            Feuille de style (thème clair et sombre, animations)
  static/js/             JavaScript : thème, impression, simulation de la démo en ligne
manage.py                Point d'entrée Django (à la racine)
```

Le thème clair ou sombre suit le réglage de l'ordinateur ; le bouton en haut à droite permet de le changer,
et le choix est mémorisé dans le navigateur.
