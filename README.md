# Gestion Atelier

Application web de gestion des données d'atelier : stock de pièces d'usure et de consommables,
arborescence d'outillage, fiches produit par machine, avec quatre niveaux d'accès.

Cette version est une **démo** avec des données fictives, destinée à présenter le projet.

## Ce que montre la démo

- **Stock** : articles avec type d'inventaire, emplacement, stock mini et quantité mini de commande,
  plusieurs fournisseurs dont un préféré, sorties et entrées de stock. Chaque article est soit acheté
  (commandé sur la référence du fournisseur), soit un design interne (commandé sur son numéro de plan).
  Création et modification des articles et des fournisseurs dans l'application (selon les droits, par défaut Méthode et Intendant).
- **Import et export Excel** : export de tous les articles, modèle vide, import avec aperçu des créations,
  modifications et erreurs avant tout enregistrement.
- **À commander** : articles sous le stock mini, regroupés par fournisseur préféré, imprimable.
- **Commandes** : suivi des commandes fournisseurs (numéro, n° fournisseur, prix, délai, dates,
  état en attente / passée / reçue / réceptionnée / annulée), retards signalés, filtres par état,
  fournisseur et retard. Une commande se prépare depuis « À commander » ; à la réception, les quantités
  livrées entrent en stock (livraison partielle possible). Dans le stock, la fiche article, l'accueil
  et « À commander », un article bas en stock affiche ses commandes en cours.
- **Inventaires tournants** : fréquence de comptage par article, feuille de comptage imprimable
  par type d'inventaire, saisie des quantités comptées qui corrige le stock (profil Intendant).
  L'écart avec le stock théorique s'affiche pendant la saisie et dans le rapport des écarts
  (par période et type, chiffré au prix du fournisseur préféré).
- **Outillage** : arborescence outil, sous-ensembles et pièces d'usure, avec leur stock.
  Le profil Méthode crée et modifie les outils et leurs pièces directement dans l'application ;
  depuis la fiche d'un outil, tous les profils sortent du stock une pièce remplacée.
- **Produits et machines** : une matrice avec une ligne par produit et une colonne par machine.
  Chaque case a un état : programmé, à faire (affiché « à sécuriser » quand le produit tourne déjà
  sur une autre machine), non faisable, ou vide (rien de prévu mais possible). Un clic sur une case
  change son état, ouvre la fiche, la crée ou la copie depuis une autre machine.
- **Fiches production** : cadence, paramètres de réglage structurés (libellé, valeur, unité), outillages,
  consommables, notes, photos et documents (plan PDF, tableur…), imprimable. Création et modification
  dans l'application ; une nouvelle fiche reprend les libellés de paramètres de la machine. Une fiche
  se copie vers une autre machine, un produit se duplique avec toutes ses fiches.
- **Profils et droits** : `Admin`, `Méthode et management`, `Intendant`, `Régleur`, `Opérateur`.
  Les droits de chaque profil se règlent sur la page **Droits** (profil Admin) : cinq blocs
  (stock, commandes, outillage, produits, administration) découpés en sous-fonctions, avec
  le profil de chaque compte. Le catalogue et les réglages de départ sont dans
  `backend/comptes/droits.py` : l'intendant gère commandes, articles, fournisseurs et comptages ;
  le régleur a en plus de l'opérateur les photos et documents et les réglages des fiches.

Comptes de démonstration, tous avec le mot de passe `demo` :
`admin`, `methode`, `chef`, `regleur`, `intendante`, `operateur`.

## Démo en ligne

Une version statique de la démo est publiée sur GitHub Pages :
https://noriviere.github.io/Gestion-Atelier/

On y choisit un profil (Admin, Méthode et management, Intendant, Régleur, Opérateur) pour voir l'application
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

L'application répond sur le port 8000, avec une base PostgreSQL. Les photos et documents des fiches
sont stockés dans le volume Docker `documents` (à inclure dans la sauvegarde avec la base).

## Modifier les données fictives

Toutes les données de la démo sont dans [`demo/donnees.py`](demo/donnees.py), sous forme de listes
simples. Après modification, `python manage.py charger_demo` efface et recharge tout.

## Règles de calcul

- Un article est **à commander** quand son stock est inférieur ou égal au stock mini.
- La **quantité suggérée** ramène le stock au niveau du mini, plus le mini de commande :
  `max(mini de commande, stock mini − stock + mini de commande)`.
- La **quantité en commande** d'un article additionne ses lignes de commandes en attente, passées ou reçues
  (pas encore entrées en stock). Un article sous le mini est **couvert** quand stock + en commande dépasse
  le stock mini ; sinon le **reste à commander** applique la règle ci-dessus au stock prévisionnel.
- Une commande passée est **en retard** quand sa date de livraison prévue est dépassée. Au passage de la
  commande, la date prévue est calculée avec le délai le plus long du fournisseur pour ses articles,
  sauf si elle est saisie.
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
