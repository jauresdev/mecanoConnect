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

Chaque réparateur peut ajouter une photo principale (JPG, PNG ou WebP, 5 Mo maximum) et renseigner les horaires jour par jour. En développement, Django sert les images depuis `MEDIA_ROOT` (`media/`). En production, configurez un stockage persistant pour les fichiers média et servez-les via HTTPS.

Les réparateurs peuvent copier les coordonnées d'un point dans Google Maps et les coller dans le champ de localisation (ou coller un lien Google Maps complet contenant les coordonnées) pour faire apparaître leur atelier sur la carte des résultats.

La carte des résultats utilise Google Maps lorsqu'une clé est configurée. Pour l'activer en local, créez un fichier `.env.local` à la racine du frontend et ajoutez `VITE_GOOGLE_MAPS_API_KEY=<votre-clé>`. Activez la facturation Google et l'API Maps JavaScript, puis restreignez la clé à cette API et aux URL de votre application. Ne publiez pas une clé non restreinte. Si la clé est absente ou invalide, une carte OpenStreetMap interactive s'affiche automatiquement. Le visiteur peut cliquer sur **Me localiser** pour calculer les distances à vol d'oiseau : sa position est demandée uniquement après ce clic et n'est pas enregistrée. Les garages à moins de 5 km sont verts, ceux entre 5 et 15 km orange, et ceux à plus de 15 km rouges.

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
| `GET/POST/PUT/PATCH/DELETE` | `/api/vehicles/` | Véhicules enregistrés du client connecté |
| `GET/POST` | `/api/quotes/` | Demandes du client; côté réparateur, demandes de ses ateliers |
| `POST` | `/api/quotes/{id}/accept-request/`, `/decline-request/` | Propriétaire de l'atelier |
| `POST` | `/api/quotes/{id}/message/` | Client ou réparateur concerné |
| `POST` | `/api/quotes/{id}/offers/` | Propriétaire de l'atelier; crée une nouvelle version du devis |
| `POST` | `/api/quotes/{id}/decide/`, `/request-changes/` | Client à l'origine |
| `POST` | `/api/quotes/{id}/appointments/` | Propriétaire de l'atelier, après acceptation du devis |
| `GET` | `/api/appointments/` | Calendrier du client ou des ateliers du réparateur |
| `POST` | `/api/appointments/{id}/confirm/`, `/cancel/` | Confirmation par le client; annulation par un participant |
| `GET` | `/api/notifications/` | Notifications du compte connecté |
| `POST` | `/api/notifications/{id}/read/` | Destinataire de la notification |
| `POST` | `/api/quotes/{id}/report/` | Client ou réparateur participant |
| `GET` | `/api/reports/` | Administrateur |
| `POST` | `/api/reports/{id}/resolve/` | Administrateur |
| `POST` | `/api/quotes/{id}/respond/` | Propriétaire de l'atelier |
| `POST` | `/api/quotes/{id}/start/`, `/complete/`, `/cancel/` | Participants selon la transition; compatibilité historique |
| `GET/POST` | `/api/reviews/` | Avis approuvés publics; publication réservée au client avec devis terminé |

## Interventions, devis et rendez-vous

Le client enregistre d'abord ses véhicules via `/api/vehicles/`, puis en choisit un dans le formulaire d'intervention. Une demande existante reste liée à un atelier précis et à un type de véhicule pris en charge : elle n'est pas diffusée à tous les professionnels. Le client décrit la panne (moteur, électricité, freinage, batterie, pneumatique, entretien, accident ou autre), ajoute une localisation, ses disponibilités, le mode d'intervention et jusqu'à quatre photos. Les photos de demande sont stockées dans `private_uploads/`, hors du répertoire média public, et téléchargées par une route API authentifiée accessible uniquement au client, au propriétaire de l'atelier concerné et aux administrateurs. En production, configurez un stockage persistant et sauvegardé pour ce répertoire privé.

Le mécanicien accepte ou refuse la demande, peut échanger des messages, puis envoie un devis estimatif structuré. Le corps de `POST /api/quotes/{id}/offers/` contient `description`, `parts` (liste de `{name, quantity, unit_price}`), `labor_cost`, `travel_cost`, `estimated_duration_minutes`, `valid_until` et `conditions`. Tous les montants sont des nombres entiers en FCFA (XOF) et le total est recalculé côté serveur. Les versions antérieures sont conservées et un devis expiré ne peut plus être accepté. Le client peut accepter, refuser ou demander une révision via `/decide/` ou `/request-changes/`. Un devis accepté n'est pas une facture. Si un supplément est proposé pendant une réparation, l'intervention est suspendue jusqu'à l'accord du client; refuser ce supplément ne supprime pas le devis initial déjà accepté.

Après acceptation, le réparateur propose un créneau avec `scheduled_at` (date ISO 8601 avec fuseau) et une note facultative. Le client le confirme. Un créneau confirmé bloque les chevauchements dans le calendrier de l'atelier. Un rendez-vous futur peut être annulé par l'un ou l'autre participant; un report se fait en annulant le créneau puis en proposant une nouvelle date. La demande ne peut passer « en cours » qu'après confirmation du rendez-vous dans le nouveau parcours. Les anciennes demandes conservent leurs transitions historiques via `/respond/`, `/start/` et `/complete/`.

Les transitions et décisions significatives créent un événement d'historique et une notification interne. Les clients et mécaniciens ne voient que les demandes auxquelles ils participent. Les administrateurs consultent l'historique dans Django Admin, traitent les signalements depuis `/api/reports/` ou l'interface d'administration et ne peuvent pas modifier directement les états d'intervention hors du workflow.

Après une réparation terminée, le client peut laisser une note de 1 à 5 étoiles et un commentaire facultatif. Les avis sont masqués jusqu'à leur approbation par un administrateur.

## Contrôles

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
