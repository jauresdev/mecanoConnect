# MécanoConnect — backend

API REST Django pour l'annuaire de réparateurs, les comptes, les demandes de devis et les avis. Les données visibles dans la maquette React restent fictives jusqu'à leur remplacement par des ateliers enregistrés dans l'API.

## Prérequis et lancement local

- Python 3.10 ou plus récent
- Node.js et npm
- Une base SQLite (configuration locale par défaut)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Le serveur écoute sur `http://127.0.0.1:8000`. L'interface d'administration est disponible à `/admin/`, l'état de santé à `/api/health/` et la documentation OpenAPI/Swagger à `/api/docs/`.

Dans un second terminal, lancer le frontend :

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

Le frontend est disponible à `http://127.0.0.1:5174/` et relaie `/api` vers le backend local (`http://127.0.0.1:8003`). Pour lancer le backend sur ce port, utiliser `python manage.py runserver 127.0.0.1:8003`. Si le port 8000 est libre, lancer Vite avec `API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5174`.

Le lien **Se connecter** ouvre le formulaire de connexion. **Mécanicien** permet de créer un compte réparateur; après inscription et connexion, le tableau de bord `/#mecanicien` permet d'ajouter un atelier et de répondre aux demandes reçues. Les visiteurs peuvent parcourir le catalogue sans compte; les devis nécessitent un compte client. Après connexion, le client retrouve les réponses et le suivi dans `/#client`.

Après l'ajout d'un atelier, le formulaire se ferme. Le tableau de bord permet ensuite de modifier chaque fiche, filtrer les demandes, répondre aux devis et marquer une intervention acceptée comme terminée. La modification d'une fiche est réservée à son propriétaire.

## PostgreSQL

Créer une base et un utilisateur PostgreSQL, installer les dépendances ci-dessus puis configurer dans l'environnement de déploiement :

```dotenv
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<secret long et aléatoire>
DJANGO_ALLOWED_HOSTS=api.example.com
DJANGO_CORS_ALLOWED_ORIGINS=https://example.com
DB_ENGINE=postgresql
DB_NAME=mecanoconnect
DB_USER=mecanoconnect
DB_PASSWORD=<mot de passe>
DB_HOST=<hôte PostgreSQL>
DB_PORT=5432
```

Appliquer ensuite `python manage.py migrate`. En production, fournir la clé secrète via le gestionnaire de secrets de la plateforme, servir l'application derrière HTTPS et ne pas activer `DJANGO_DEBUG`.

## Authentification et rôles

- `POST /api/auth/register/` crée un compte `customer` ou `mechanic`. Le rôle administrateur est attribué uniquement via Django Admin/`createsuperuser`.
- `POST /api/auth/token/` reçoit `username` et `password`, et renvoie les jetons JWT `access` et `refresh`.
- `POST /api/auth/token/refresh/` renouvelle le jeton d'accès.
- `GET/PATCH /api/auth/me/` lit ou modifie le profil (prénom, nom, téléphone).
- Envoyer `Authorization: Bearer <access>` pour les opérations authentifiées.

## Ressources principales

| Méthode | URL | Accès |
|---|---|---|
| `GET` | `/api/services/`, `/api/vehicle-types/` | Public |
| `GET` | `/api/shops/`, `/api/shops/{id}/` | Public |
| `POST` | `/api/shops/` | Réparateur |
| `PUT/PATCH/DELETE` | `/api/shops/{id}/` | Propriétaire (suppression logique) ou administrateur |
| `GET` | `/api/shops/?city=Parakou&district=Banikanni&vehicle=moto&service=freins&mobile_service=true&search=garage` | Public, filtres combinables |
| `GET` | `/api/shops/{id}/reviews/` | Avis approuvés publics |
| `GET/POST` | `/api/quotes/` | Client authentifié (les réparateurs voient les demandes de leurs ateliers) |
| `POST` | `/api/quotes/{id}/respond/` | Propriétaire de l'atelier |
| `POST` | `/api/quotes/{id}/decide/`, `/complete/`, `/cancel/` | Client à l'origine |
| `GET/POST` | `/api/reviews/` | Avis approuvés publics; publication réservée au client avec devis terminé |

Une réponse réparateur attend `{"response":"..."}`. Le client la retrouve dans son espace après connexion et répond avec `{"decision":"accepted"}` ou `{"decision":"declined"}` sur `/decide/`. Après acceptation, le propriétaire peut marquer la réparation « en cours » avec `/start/`, puis « terminée » avec `/complete/`. Les avis sont masqués jusqu'à leur approbation par un administrateur. Les demandes de devis sont privées : seuls leur client, le réparateur concerné et les administrateurs peuvent les consulter.

## Contrôles

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
