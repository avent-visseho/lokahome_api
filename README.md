# LOKAHOME API

Backend FastAPI pour LOKAHOME — plateforme de location immobilière au Bénin avec marketplace de services intégrée.

## Stack

- **FastAPI** (Python 3.12+) — API REST asynchrone
- **PostgreSQL** + **PostGIS** — base de données géospatiale
- **Redis** — cache + broker Celery
- **Celery** — tâches asynchrones (emails, notifications, paiements)
- **SQLAlchemy 2** (asyncpg) — ORM async
- **Alembic** — migrations
- **JWT** (passlib + bcrypt) — authentification

---

## ⚠️ SÉCURITÉ — Clés à régénérer

> **Important** : suite au nettoyage de l'historique git, les clés suivantes ont été exposées localement et **doivent être régénérées** avant tout déploiement en production. Ne jamais réutiliser les anciennes valeurs.

À régénérer impérativement :

| Service | Variable(s) `.env` | Où régénérer |
|---|---|---|
| **FedaPay** (paiement) | `FEDAPAY_API_KEY`, `FEDAPAY_SECRET_KEY`, `FEDAPAY_WEBHOOK_SECRET` | Dashboard FedaPay → API Keys → Revoke + Create new |
| **Firebase** (push notifications) | `firebase-credentials.json` (service account) | Google Cloud Console → IAM & Admin → Service Accounts → supprimer l'ancienne clé et en générer une nouvelle |
| **Stripe** (paiements internationaux) | `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` | Dashboard Stripe → Developers → API keys → Roll key |
| **JWT** | `SECRET_KEY` | `openssl rand -hex 32` |
| **SMTP / Email** | `MAIL_USERNAME`, `MAIL_PASSWORD` | Si mot de passe d'application Gmail / autre fournisseur exposé : révoquer + recréer |
| **Twilio SMS** | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Dashboard Twilio → Account → Auth Tokens → Create secondary + promote |
| **S3 / MinIO** | `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Console MinIO ou IAM AWS → revoke + create |
| **Super Admin** | `SUPERADMIN_PASSWORD` | Choisir un nouveau mot de passe fort |

### Règles à respecter

- Ne **jamais** committer `.env` ni `firebase-credentials.json` (déjà dans `.gitignore`)
- Toujours partir de `.env.example` puis remplir localement
- En production, utiliser un secret manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault, ou variables d'environnement de la plateforme d'hébergement)
- Activer la **rotation périodique** des clés (tous les 90 jours minimum)

---

## Démarrage rapide

### Premier setup

```bash
# Copier la config et la remplir avec des clés FRAÎCHES (cf. tableau ci-dessus)
cp .env.example .env
$EDITOR .env

# Placer firebase-credentials.json à la racine (téléchargé depuis Google Cloud Console)
# Ne PAS le committer.

# Installation (venv + dépendances)
./start.sh install

# Démarrage en mode développement
./start.sh dev
```

L'API sera disponible sur `http://localhost:8000`
- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

### Démarrage avec Docker

```bash
./start.sh docker
# ou
docker-compose up -d
```

---

## Commandes utiles

### Base de données

```bash
# Créer une migration
alembic revision --autogenerate -m "description"

# Appliquer les migrations
alembic upgrade head

# Accès shell PostgreSQL (Docker)
docker-compose exec db psql -U lokahome -d lokahome
```

### Tests

```bash
pytest -v --cov=app                    # tous les tests + coverage
pytest tests/unit/test_auth.py -v      # un fichier
pytest -k "test_login" -v              # filtrer par nom
pytest -m "not slow" -v                # ignorer les tests lents
```

### Qualité de code

```bash
ruff check app --fix     # linting + auto-fix
black app tests          # formatage
isort app tests          # tri imports
mypy app                 # type checking
```

### Celery

```bash
celery -A app.tasks worker --loglevel=info
celery -A app.tasks beat --loglevel=info
```

---

## Architecture

Clean Architecture, dépendances orientées vers l'intérieur :

```
Endpoints (api/v1/endpoints/) → Services (services/) → Repositories (repositories/) → Models (models/)
         ↓                           ↓                          ↓
   Schémas Pydantic            Logique métier             SQLAlchemy ORM
```

### Couches

- **`api/v1/endpoints/`** — routes FastAPI, validation Pydantic
- **`services/`** — logique métier, orchestre les repositories
- **`repositories/`** — accès données via `BaseRepository[ModelType]`
- **`models/`** — SQLAlchemy, héritent de `BaseModel` (UUID + timestamps)
- **`schemas/`** — Pydantic, héritent de `BaseSchema`
- **`tasks/`** — tâches Celery (email, notifications, paiements, maintenance)

### Dépendances DI (`app/api/deps.py`)

- `DbSession` — session SQLAlchemy async
- `CurrentUser`, `ActiveUser`, `VerifiedUser` — utilisateur authentifié
- `RequireTenant`, `RequireLandlord`, `RequireProvider`, `RequireAdmin` — rôles

Hiérarchie : Admin > Landlord > Tenant. `RequireLandlord` accepte landlord et admin.

### Conventions nommage SQLAlchemy

Noms réservés à éviter dans les modèles :
- `metadata` → utiliser `extra_data` pour les champs JSON
- `property` → utiliser `booked_property` pour la relation Booking→Property

---

## Endpoints principaux

Tous préfixés par `/api/v1`.

| Module | Routes principales |
|---|---|
| **Auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| **Properties** | `GET/POST /properties`, `GET /properties/{id}`, `POST /properties/nearby` |
| **Bookings** | `POST /bookings`, `GET /bookings/my-bookings`, `POST /bookings/{id}/approve` |
| **Payments** | `POST /payments/booking/{id}`, webhooks `/payments/webhook/{provider}` |
| **Services** | `GET/POST /services/providers`, `GET/POST /services/requests`, quotes |
| **Messages** | `WS /messages/ws`, `GET /messages/conversations`, notifications |
| **Reviews** | `GET/POST /reviews/property/{id}`, `/reviews/user/{id}`, `/reviews/provider/{id}` |
| **Admin** | `GET /admin/dashboard`, gestion users/properties/payments |

Voir Swagger UI pour la liste complète : `http://localhost:8000/docs`

---

## Authentification

1. `POST /auth/login` (form OAuth2 : `username` = email, `password`) → `access_token` + `refresh_token`
2. Access token : 30 min (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
3. Refresh token : 7 jours (`REFRESH_TOKEN_EXPIRE_DAYS`)
4. Header : `Authorization: Bearer <access_token>`
5. Refresh : `POST /auth/refresh` avec le refresh token

Règles mot de passe : min 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre.

---

## Fournisseurs de paiement intégrés

- **FedaPay** — flux redirect + webhook (principal, Bénin)
- **MTN MoMo** — request-to-pay via USSD
- **Moov Money** — USSD
- **Stripe** — paiements internationaux

Webhooks : `POST /api/v1/payments/webhook/{provider}`

---

## Documentation

- `docs/document-_technique.md` — spécification technique complète
- `docs/toitplus_objectif_info.md` — objectifs métier et roadmap
- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

---

## Licence

Propriétaire — © LOKAHOME
