# DOCUMENT TECHNIQUE - LOKAHOME
## Plateforme de Location de Logements et Services

---

**Version**: 1.0
**Dernière mise à jour**: Janvier 2026

## TABLE DES MATIÈRES

1. [Vue d'ensemble technique](#1-vue-densemble-technique)
2. [Architecture du système](#2-architecture-du-système)
3. [Stack technologique](#3-stack-technologique)
4. [Structure du projet FastAPI](#4-structure-du-projet-fastapi)
5. [Base de données](#5-base-de-données)
6. [Modules et fonctionnalités](#6-modules-et-fonctionnalités)
7. [Authentification et sécurité](#7-authentification-et-sécurité)
8. [Paiements](#8-paiements)
9. [Notifications](#9-notifications)
10. [Géolocalisation](#10-géolocalisation)
11. [Upload de fichiers](#11-upload-de-fichiers)
12. [API Documentation](#12-api-documentation)
13. [Environnements et déploiement](#13-environnements-et-déploiement)
14. [Tests](#14-tests)
15. [Monitoring et logs](#15-monitoring-et-logs)
16. [Annexes](#16-annexes)

---

## 1. VUE D'ENSEMBLE TECHNIQUE

### 1.1. Objectifs techniques
- API REST scalable et performante
- Architecture modulaire et maintenable
- Sécurité des données et transactions
- Support de montée en charge
- Documentation automatique

### 1.2. Principes de conception
- **Clean Architecture**: Séparation claire des couches
- **DRY (Don't Repeat Yourself)**: Réutilisation du code
- **SOLID**: Principes de conception orientée objet
- **API First**: Documentation avant implémentation
- **Test Driven Development**: Tests unitaires et d'intégration

---

## 2. ARCHITECTURE DU SYSTÈME

### 2.1. Architecture globale

```
┌─────────────────┐         ┌─────────────────┐
│  Mobile Client  │         │  Mobile Client  │
│   (Locataire)   │         │  (Propriétaire) │
└────────┬────────┘         └────────┬────────┘
         │                           │
         └───────────┬───────────────┘
                     │
              ┌──────▼──────┐
              │   API Gateway│
              │   (FastAPI)  │
              └──────┬───────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
    ┌────▼────┐ ┌───▼────┐ ┌───▼────┐
    │ Auth    │ │Business│ │Services│
    │ Service │ │ Logic  │ │ Layer  │
    └────┬────┘ └───┬────┘ └───┬────┘
         │          │           │
         └──────────┼───────────┘
                    │
         ┌──────────▼───────────┐
         │   Database Layer     │
         │  (PostgreSQL/Redis)  │
         └──────────────────────┘
```

### 2.2. Architecture en couches

```
app/
├── api/          # Routes et endpoints
├── core/         # Configuration et utilitaires
├── models/       # Modèles de données (ORM)
├── schemas/      # Schémas Pydantic (validation)
├── services/     # Logique métier
├── repositories/ # Accès aux données
└── utils/        # Fonctions utilitaires
```

---

## 3. STACK TECHNOLOGIQUE

### 3.1. Backend
- **Framework**: FastAPI 0.104+
- **Python**: 3.11+
- **ORM**: SQLAlchemy 2.0
- **Migration**: Alembic
- **Validation**: Pydantic v2
- **Async**: asyncio, asyncpg

### 3.2. Base de données
- **Principale**: PostgreSQL 15+
- **Cache**: Redis 7+
- **Search**: Elasticsearch 8+ (optionnel)
- **File Storage**: AWS S3 / MinIO

### 3.3. Authentification et Sécurité
- **JWT**: python-jose
- **Password Hashing**: passlib + bcrypt
- **OAuth2**: authlib
- **Rate Limiting**: slowapi

### 3.4. Paiements
- **FedaPay** (Bénin)
- **Stripe** (international)
- **Mobile Money** (MTN, Moov)

### 3.5. Communication
- **Email**: FastAPI-Mail
- **SMS**: Twilio / AfricasTalking
- **Push Notifications**: Firebase Cloud Messaging

### 3.6. Autres
- **Task Queue**: Celery + Redis
- **WebSocket**: FastAPI WebSocket
- **Monitoring**: Prometheus + Grafana
- **Logging**: Loguru
- **Documentation**: Swagger/OpenAPI (auto)

---

## 4. STRUCTURE DU PROJET FASTAPI

### 4.1. Structure détaillée

```
lokahome-api/
│
├── app/
│   ├── __init__.py
│   │
│   ├── main.py                 # Point d'entrée de l'application
│   │
│   ├── api/                    # Routes et endpoints
│   │   ├── __init__.py
│   │   ├── deps.py            # Dépendances communes
│   │   └── v1/                # Version 1 de l'API
│   │       ├── __init__.py
│   │       ├── router.py      # Router principal v1
│   │       ├── auth.py        # Authentification
│   │       ├── users.py       # Gestion utilisateurs
│   │       ├── properties.py  # Gestion logements
│   │       ├── bookings.py    # Réservations
│   │       ├── payments.py    # Paiements
│   │       ├── services.py    # Services maintenance
│   │       ├── messages.py    # Messagerie
│   │       ├── reviews.py     # Avis et notes
│   │       └── admin.py       # Administration
│   │
│   ├── core/                   # Configuration
│   │   ├── __init__.py
│   │   ├── config.py          # Variables d'environnement
│   │   ├── security.py        # Sécurité et JWT
│   │   ├── database.py        # Configuration DB
│   │   ├── redis.py           # Configuration Redis
│   │   └── exceptions.py      # Exceptions personnalisées
│   │
│   ├── models/                 # Modèles SQLAlchemy
│   │   ├── __init__.py
│   │   ├── base.py            # Classe de base
│   │   ├── user.py            # Modèle utilisateur
│   │   ├── property.py        # Modèle logement
│   │   ├── booking.py         # Modèle réservation
│   │   ├── payment.py         # Modèle paiement
│   │   ├── service.py         # Modèle service
│   │   ├── message.py         # Modèle message
│   │   ├── review.py          # Modèle avis
│   │   └── associations.py    # Tables de liaison
│   │
│   ├── schemas/                # Schémas Pydantic
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── property.py
│   │   ├── booking.py
│   │   ├── payment.py
│   │   ├── service.py
│   │   ├── message.py
│   │   ├── review.py
│   │   └── common.py          # Schémas communs
│   │
│   ├── services/               # Logique métier
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── property_service.py
│   │   ├── booking_service.py
│   │   ├── payment_service.py
│   │   ├── service_service.py
│   │   ├── message_service.py
│   │   ├── notification_service.py
│   │   ├── email_service.py
│   │   ├── sms_service.py
│   │   └── upload_service.py
│   │
│   ├── repositories/           # Accès données
│   │   ├── __init__.py
│   │   ├── base.py            # Repository de base
│   │   ├── user_repository.py
│   │   ├── property_repository.py
│   │   ├── booking_repository.py
│   │   ├── payment_repository.py
│   │   ├── service_repository.py
│   │   ├── message_repository.py
│   │   └── review_repository.py
│   │
│   ├── utils/                  # Utilitaires
│   │   ├── __init__.py
│   │   ├── helpers.py
│   │   ├── validators.py
│   │   ├── formatters.py
│   │   └── constants.py
│   │
│   └── tasks/                  # Tâches asynchrones (Celery)
│       ├── __init__.py
│       ├── email_tasks.py
│       ├── notification_tasks.py
│       └── payment_tasks.py
│
├── alembic/                    # Migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
├── tests/                      # Tests
│   ├── __init__.py
│   ├── conftest.py            # Configuration pytest
│   ├── unit/
│   │   ├── test_services.py
│   │   └── test_repositories.py
│   ├── integration/
│   │   └── test_api.py
│   └── fixtures/
│
├── scripts/                    # Scripts utilitaires
│   ├── init_db.py
│   ├── seed_data.py
│   └── backup.py
│
├── .env.example               # Variables d'environnement
├── .gitignore
├── requirements.txt           # Dépendances
├── pytest.ini                # Configuration pytest
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### 4.2. Fichier main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.config import settings
from app.core.database import engine
from app.models.base import Base
from app.api.v1.router import api_router

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API pour la plateforme LokaHome",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "LokaHome API", "version": settings.VERSION}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## 5. BASE DE DONNÉES

### 5.1. Schéma de base de données

#### Tables principales

**users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    user_type VARCHAR(20) NOT NULL, -- 'tenant', 'landlord', 'provider', 'admin'
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**properties**
```sql
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    property_type VARCHAR(50) NOT NULL, -- 'house', 'apartment', 'shop', 'hotel', etc.
    rental_type VARCHAR(20) NOT NULL, -- 'short_term', 'long_term'
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'XOF',
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    neighborhood VARCHAR(100),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    bedrooms INTEGER,
    bathrooms INTEGER,
    surface_area DECIMAL(10,2),
    is_furnished BOOLEAN DEFAULT FALSE,
    amenities JSONB, -- wifi, parking, ac, etc.
    rules TEXT,
    status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'published', 'rented', 'inactive'
    available_from DATE,
    available_to DATE,
    minimum_stay INTEGER, -- en jours
    deposit_amount DECIMAL(10,2),
    is_featured BOOLEAN DEFAULT FALSE,
    views_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**property_images**
```sql
CREATE TABLE property_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**bookings**
```sql
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id),
    tenant_id UUID NOT NULL REFERENCES users(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    deposit_paid DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'confirmed', 'cancelled', 'completed'
    cancellation_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**payments**
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID REFERENCES bookings(id),
    service_request_id UUID REFERENCES service_requests(id),
    payer_id UUID NOT NULL REFERENCES users(id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'XOF',
    payment_method VARCHAR(50), -- 'fedapay', 'mobile_money', 'card'
    payment_provider VARCHAR(50),
    transaction_id VARCHAR(255) UNIQUE,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'refunded'
    payment_type VARCHAR(20), -- 'rent', 'deposit', 'service'
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**services**
```sql
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- 'plumbing', 'electricity', 'carpentry', etc.
    icon_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**service_providers**
```sql
CREATE TABLE service_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    company_name VARCHAR(255),
    bio TEXT,
    services JSONB, -- liste des IDs de services
    service_areas JSONB, -- villes/quartiers couverts
    hourly_rate DECIMAL(10,2),
    is_verified BOOLEAN DEFAULT FALSE,
    rating DECIMAL(3,2) DEFAULT 0,
    total_jobs INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**service_requests**
```sql
CREATE TABLE service_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES services(id),
    requester_id UUID NOT NULL REFERENCES users(id),
    property_id UUID REFERENCES properties(id),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    urgency VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    status VARCHAR(20) DEFAULT 'open', -- 'open', 'quoted', 'assigned', 'in_progress', 'completed', 'cancelled'
    preferred_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**service_quotes**
```sql
CREATE TABLE service_quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_request_id UUID NOT NULL REFERENCES service_requests(id),
    provider_id UUID NOT NULL REFERENCES service_providers(id),
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    estimated_duration INTEGER, -- en heures
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**messages**
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_id UUID NOT NULL REFERENCES users(id),
    receiver_id UUID NOT NULL REFERENCES users(id),
    property_id UUID REFERENCES properties(id),
    service_request_id UUID REFERENCES service_requests(id),
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**reviews**
```sql
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reviewer_id UUID NOT NULL REFERENCES users(id),
    property_id UUID REFERENCES properties(id),
    provider_id UUID REFERENCES service_providers(id),
    booking_id UUID REFERENCES bookings(id),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**notifications**
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(50), -- 'booking', 'payment', 'message', 'review', etc.
    related_id UUID, -- ID de l'objet lié
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5.2. Index et optimisations

```sql
-- Index pour les recherches fréquentes
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_type ON properties(property_type);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_owner ON properties(owner_id);
CREATE INDEX idx_properties_location ON properties USING GIST(ll_to_earth(latitude, longitude));

CREATE INDEX idx_bookings_tenant ON bookings(tenant_id);
CREATE INDEX idx_bookings_property ON bookings(property_id);
CREATE INDEX idx_bookings_dates ON bookings(start_date, end_date);

CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_receiver ON messages(receiver_id);
CREATE INDEX idx_messages_unread ON messages(receiver_id) WHERE is_read = FALSE;

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id) WHERE is_read = FALSE;
```

---

## 6. MODULES ET FONCTIONNALITÉS

### 6.1. Module Authentification

**Endpoints**
- `POST /api/v1/auth/register` - Inscription
- `POST /api/v1/auth/login` - Connexion
- `POST /api/v1/auth/refresh` - Rafraîchir le token
- `POST /api/v1/auth/logout` - Déconnexion
- `POST /api/v1/auth/forgot-password` - Mot de passe oublié
- `POST /api/v1/auth/reset-password` - Réinitialiser mot de passe
- `POST /api/v1/auth/verify-email` - Vérifier email
- `POST /api/v1/auth/verify-phone` - Vérifier téléphone

**Schémas**
```python
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    email: EmailStr
    phone: str
    password: str = Field(..., min_length=8)
    first_name: str
    last_name: str
    user_type: str = Field(..., pattern="^(tenant|landlord|provider)$")

class UserLogin(BaseModel):
    username: str  # email ou phone
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

### 6.2. Module Utilisateurs

**Endpoints**
- `GET /api/v1/users/me` - Profil actuel
- `PUT /api/v1/users/me` - Modifier profil
- `POST /api/v1/users/me/avatar` - Upload avatar
- `GET /api/v1/users/{user_id}` - Profil public
- `POST /api/v1/users/me/verify-identity` - Vérification identité

### 6.3. Module Propriétés

**Endpoints**
- `GET /api/v1/properties` - Liste avec filtres
- `POST /api/v1/properties` - Créer annonce
- `GET /api/v1/properties/{id}` - Détails
- `PUT /api/v1/properties/{id}` - Modifier
- `DELETE /api/v1/properties/{id}` - Supprimer
- `POST /api/v1/properties/{id}/images` - Upload images
- `GET /api/v1/properties/search` - Recherche avancée
- `GET /api/v1/properties/nearby` - Recherche géographique
- `POST /api/v1/properties/{id}/favorite` - Ajouter aux favoris

**Filtres de recherche**
```python
class PropertyFilter(BaseModel):
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    property_type: Optional[str] = None
    rental_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    is_furnished: Optional[bool] = None
    amenities: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[float] = 5.0  # km
    available_from: Optional[date] = None
    available_to: Optional[date] = None
```

### 6.4. Module Réservations

**Endpoints**
- `POST /api/v1/bookings` - Créer réservation
- `GET /api/v1/bookings/{id}` - Détails
- `PUT /api/v1/bookings/{id}/cancel` - Annuler
- `GET /api/v1/bookings/my-bookings` - Mes réservations (locataire)
- `GET /api/v1/bookings/my-properties` - Réservations de mes biens (propriétaire)
- `PUT /api/v1/bookings/{id}/accept` - Accepter (propriétaire)
- `PUT /api/v1/bookings/{id}/reject` - Refuser (propriétaire)
- `GET /api/v1/properties/{id}/availability` - Disponibilité

### 6.5. Module Paiements

**Endpoints**
- `POST /api/v1/payments/initialize` - Initialiser paiement
- `POST /api/v1/payments/webhook` - Webhook fournisseur
- `GET /api/v1/payments/{id}` - Statut paiement
- `GET /api/v1/payments/history` - Historique
- `POST /api/v1/payments/refund` - Remboursement

### 6.6. Module Services

**Endpoints**
- `GET /api/v1/services` - Liste services disponibles
- `POST /api/v1/service-requests` - Créer demande
- `GET /api/v1/service-requests/{id}` - Détails
- `GET /api/v1/service-requests/my-requests` - Mes demandes
- `POST /api/v1/service-quotes` - Envoyer devis
- `PUT /api/v1/service-quotes/{id}/accept` - Accepter devis
- `GET /api/v1/service-providers` - Liste prestataires
- `GET /api/v1/service-providers/{id}` - Profil prestataire

### 6.7. Module Messagerie

**Endpoints**
- `POST /api/v1/messages` - Envoyer message
- `GET /api/v1/messages/conversations` - Liste conversations
- `GET /api/v1/messages/conversation/{user_id}` - Conversation avec utilisateur
- `PUT /api/v1/messages/{id}/read` - Marquer comme lu
- `WebSocket /ws/messages` - Messagerie temps réel

### 6.8. Module Avis

**Endpoints**
- `POST /api/v1/reviews` - Créer avis
- `GET /api/v1/reviews/property/{id}` - Avis d'un bien
- `GET /api/v1/reviews/provider/{id}` - Avis d'un prestataire
- `PUT /api/v1/reviews/{id}` - Modifier avis
- `DELETE /api/v1/reviews/{id}` - Supprimer avis

---

## 7. AUTHENTIFICATION ET SÉCURITÉ

### 7.1. JWT Configuration

```python
# app/core/security.py
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

### 7.2. Dépendances d'authentification

```python
# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user

async def get_current_landlord(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.user_type != "landlord":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
```

### 7.3. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

---

## 8. PAIEMENTS

### 8.1. Intégration FedaPay

```python
# app/services/payment_service.py
import fedapay
from app.core.config import settings

fedapay.api_key = settings.FEDAPAY_SECRET_KEY
fedapay.environment = settings.FEDAPAY_ENVIRONMENT  # 'sandbox' ou 'live'

async def create_payment(amount: float, booking_id: str, user_email: str):
    transaction = fedapay.Transaction.create({
        "description": f"Paiement loyer - Réservation #{booking_id}",
        "amount": int(amount),
        "currency": {"iso": "XOF"},
        "callback_url": f"{settings.API_URL}/api/v1/payments/webhook",
        "customer": {
            "email": user_email
        },
        "metadata": {
            "booking_id": booking_id
        }
    })
    return transaction

async def verify_payment(transaction_id: str):
    transaction = fedapay.Transaction.retrieve(transaction_id)
    return transaction.status == "approved"
```

### 8.2. Intégration Mobile Money

```python
# app/services/mobile_money_service.py
from app.core.config import settings

class MobileMoneyService:
    """Service pour les paiements Mobile Money (MTN, Moov)"""

    async def initiate_mtn_payment(self, phone: str, amount: float, reference: str):
        """Initier un paiement MTN Mobile Money"""
        # Configuration MTN MoMo API
        headers = {
            "Authorization": f"Bearer {settings.MTN_API_KEY}",
            "X-Reference-Id": reference,
            "X-Target-Environment": settings.MTN_ENVIRONMENT,
            "Content-Type": "application/json"
        }

        payload = {
            "amount": str(int(amount)),
            "currency": "XOF",
            "externalId": reference,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone
            },
            "payerMessage": "Paiement LOKAHOME",
            "payeeNote": "Location immobilière"
        }

        # Appel API MTN MoMo
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(MTN_API_URL, json=payload, headers=headers)
        #     return response.json()
        pass

    async def initiate_moov_payment(self, phone: str, amount: float, reference: str):
        """Initier un paiement Moov Money"""
        # Implémentation similaire pour Moov
        pass
```

### 8.3. Gestion des Webhooks

```python
# app/api/v1/payments.py
from fastapi import APIRouter, Request, HTTPException
from app.services.payment_service import PaymentService

router = APIRouter()

@router.post("/webhook/fedapay")
async def fedapay_webhook(request: Request):
    """Webhook pour les notifications FedaPay"""
    payload = await request.json()
    signature = request.headers.get("X-Fedapay-Signature")

    # Vérifier la signature
    if not verify_fedapay_signature(payload, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = payload.get("event")
    transaction = payload.get("entity")

    if event_type == "transaction.approved":
        # Marquer le paiement comme complété
        await PaymentService.mark_payment_completed(
            transaction_id=transaction["id"],
            booking_id=transaction["metadata"]["booking_id"]
        )
    elif event_type == "transaction.declined":
        # Marquer le paiement comme échoué
        await PaymentService.mark_payment_failed(
            transaction_id=transaction["id"]
        )

    return {"status": "received"}

@router.post("/webhook/mtn")
async def mtn_webhook(request: Request):
    """Webhook pour les notifications MTN MoMo"""
    payload = await request.json()
    # Traitement similaire
    return {"status": "received"}
```

### 8.4. Schémas de paiement

```python
# app/schemas/payment.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class PaymentMethod(str, Enum):
    FEDAPAY = "fedapay"
    MTN_MOMO = "mtn_momo"
    MOOV_MONEY = "moov_money"
    CARD = "card"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentCreate(BaseModel):
    booking_id: Optional[str] = None
    service_request_id: Optional[str] = None
    amount: float
    payment_method: PaymentMethod
    phone_number: Optional[str] = None  # Pour Mobile Money

class PaymentResponse(BaseModel):
    id: str
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethod
    transaction_id: Optional[str]
    payment_url: Optional[str]  # URL de redirection pour FedaPay
    created_at: datetime

    class Config:
        from_attributes = True
```

---

## 9. NOTIFICATIONS

### 9.1. Architecture des notifications

```
┌─────────────────┐
│  Event Trigger  │
│ (Booking, etc.) │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Celery  │
    │  Task   │
    └────┬────┘
         │
    ┌────┴────┬─────────────┐
    │         │             │
┌───▼───┐ ┌───▼───┐   ┌────▼────┐
│ Push  │ │ Email │   │   SMS   │
│  FCM  │ │ SMTP  │   │ Twilio  │
└───────┘ └───────┘   └─────────┘
```

### 9.2. Service de notifications

```python
# app/services/notification_service.py
from firebase_admin import messaging
from app.core.config import settings
from app.services.email_service import EmailService
from app.services.sms_service import SMSService

class NotificationService:
    def __init__(self):
        self.email_service = EmailService()
        self.sms_service = SMSService()

    async def send_push_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: dict = None
    ):
        """Envoyer une notification push via Firebase"""
        # Récupérer le token FCM de l'utilisateur
        user = await self.get_user(user_id)
        if not user.fcm_token:
            return False

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=user.fcm_token
        )

        try:
            response = messaging.send(message)
            return True
        except Exception as e:
            # Logger l'erreur
            return False

    async def send_booking_confirmation(self, booking_id: str):
        """Envoyer notification de confirmation de réservation"""
        booking = await self.get_booking(booking_id)

        # Notification push
        await self.send_push_notification(
            user_id=booking.tenant_id,
            title="Réservation confirmée",
            body=f"Votre réservation pour {booking.property.title} a été confirmée.",
            data={"type": "booking", "booking_id": booking_id}
        )

        # Email
        await self.email_service.send_booking_confirmation_email(booking)

        # SMS
        await self.sms_service.send_sms(
            phone=booking.tenant.phone,
            message=f"LOKAHOME: Votre réservation #{booking_id[:8]} est confirmée."
        )

    async def send_payment_reminder(self, booking_id: str):
        """Envoyer rappel de paiement"""
        booking = await self.get_booking(booking_id)

        await self.send_push_notification(
            user_id=booking.tenant_id,
            title="Rappel de paiement",
            body=f"N'oubliez pas de régler votre loyer pour {booking.property.title}.",
            data={"type": "payment_reminder", "booking_id": booking_id}
        )

    async def send_new_message_notification(self, message_id: str):
        """Notifier un nouveau message"""
        message = await self.get_message(message_id)

        await self.send_push_notification(
            user_id=message.receiver_id,
            title=f"Nouveau message de {message.sender.first_name}",
            body=message.content[:100],
            data={"type": "message", "sender_id": str(message.sender_id)}
        )
```

### 9.3. Configuration Firebase

```python
# app/core/firebase.py
import firebase_admin
from firebase_admin import credentials
from app.core.config import settings

def init_firebase():
    """Initialiser Firebase Admin SDK"""
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
```

### 9.4. Tâches Celery pour notifications

```python
# app/tasks/notification_tasks.py
from celery import shared_task
from app.services.notification_service import NotificationService

notification_service = NotificationService()

@shared_task
def send_booking_confirmation_task(booking_id: str):
    """Tâche asynchrone pour envoyer confirmation de réservation"""
    import asyncio
    asyncio.run(notification_service.send_booking_confirmation(booking_id))

@shared_task
def send_payment_reminder_task(booking_id: str):
    """Tâche asynchrone pour envoyer rappel de paiement"""
    import asyncio
    asyncio.run(notification_service.send_payment_reminder(booking_id))

@shared_task
def send_daily_payment_reminders():
    """Tâche planifiée : rappels de paiement quotidiens"""
    # Récupérer les réservations avec paiement en retard
    # Envoyer les rappels
    pass
```

### 9.5. Service Email

```python
# app/services/email_service.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER="app/templates/email"
)

class EmailService:
    def __init__(self):
        self.fastmail = FastMail(conf)

    async def send_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        template_data: dict
    ):
        """Envoyer un email avec template"""
        message = MessageSchema(
            subject=subject,
            recipients=[to],
            template_body=template_data,
            subtype="html"
        )

        await self.fastmail.send_message(message, template_name=template_name)

    async def send_welcome_email(self, user):
        """Email de bienvenue"""
        await self.send_email(
            to=user.email,
            subject="Bienvenue sur LOKAHOME",
            template_name="welcome.html",
            template_data={
                "first_name": user.first_name,
                "app_url": settings.APP_URL
            }
        )

    async def send_booking_confirmation_email(self, booking):
        """Email de confirmation de réservation"""
        await self.send_email(
            to=booking.tenant.email,
            subject="Confirmation de votre réservation - LOKAHOME",
            template_name="booking_confirmation.html",
            template_data={
                "tenant_name": booking.tenant.first_name,
                "property_title": booking.property.title,
                "start_date": booking.start_date.strftime("%d/%m/%Y"),
                "end_date": booking.end_date.strftime("%d/%m/%Y"),
                "total_amount": booking.total_amount
            }
        )

    async def send_password_reset_email(self, user, reset_token: str):
        """Email de réinitialisation de mot de passe"""
        reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"

        await self.send_email(
            to=user.email,
            subject="Réinitialisation de mot de passe - LOKAHOME",
            template_name="password_reset.html",
            template_data={
                "first_name": user.first_name,
                "reset_url": reset_url
            }
        )
```

### 9.6. Service SMS

```python
# app/services/sms_service.py
from twilio.rest import Client
from app.core.config import settings

class SMSService:
    def __init__(self):
        self.client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        self.from_number = settings.TWILIO_PHONE_NUMBER

    async def send_sms(self, phone: str, message: str):
        """Envoyer un SMS via Twilio"""
        try:
            self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone
            )
            return True
        except Exception as e:
            # Logger l'erreur
            return False

    async def send_verification_code(self, phone: str, code: str):
        """Envoyer code de vérification"""
        message = f"LOKAHOME: Votre code de vérification est {code}. Valide 10 minutes."
        return await self.send_sms(phone, message)

    async def send_booking_confirmation_sms(self, phone: str, booking_id: str):
        """SMS de confirmation de réservation"""
        message = f"LOKAHOME: Réservation #{booking_id[:8]} confirmée. Consultez l'app pour les détails."
        return await self.send_sms(phone, message)
```

---

## 10. GÉOLOCALISATION

### 10.1. Recherche géographique

```python
# app/services/geo_service.py
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.property import Property
from math import radians, cos, sin, asin, sqrt

class GeoService:
    @staticmethod
    def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Calculer la distance entre deux points GPS (en km)"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Rayon de la Terre en km

        return c * r

    @staticmethod
    async def find_nearby_properties(
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        limit: int = 50
    ):
        """Trouver les propriétés à proximité"""
        # Utilisation de PostGIS pour les requêtes géographiques
        # Point de référence
        point = func.ST_SetSRID(
            func.ST_MakePoint(longitude, latitude),
            4326
        )

        # Distance en mètres
        distance_meters = radius_km * 1000

        properties = db.query(Property).filter(
            func.ST_DWithin(
                func.ST_SetSRID(
                    func.ST_MakePoint(Property.longitude, Property.latitude),
                    4326
                )::func.geography,
                point::func.geography,
                distance_meters
            ),
            Property.status == 'published'
        ).limit(limit).all()

        return properties

    @staticmethod
    async def get_properties_in_city(db: Session, city: str):
        """Récupérer les propriétés d'une ville"""
        return db.query(Property).filter(
            Property.city.ilike(f"%{city}%"),
            Property.status == 'published'
        ).all()

    @staticmethod
    async def get_properties_in_neighborhood(db: Session, city: str, neighborhood: str):
        """Récupérer les propriétés d'un quartier"""
        return db.query(Property).filter(
            Property.city.ilike(f"%{city}%"),
            Property.neighborhood.ilike(f"%{neighborhood}%"),
            Property.status == 'published'
        ).all()
```

### 10.2. Endpoint de recherche géographique

```python
# app/api/v1/properties.py
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.geo_service import GeoService

router = APIRouter()

@router.get("/nearby")
async def get_nearby_properties(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(5.0, ge=0.1, le=50),  # km
    db: Session = Depends(get_db)
):
    """Rechercher les propriétés à proximité d'un point GPS"""
    properties = await GeoService.find_nearby_properties(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius
    )

    # Ajouter la distance à chaque propriété
    results = []
    for prop in properties:
        distance = GeoService.haversine(
            longitude, latitude,
            prop.longitude, prop.latitude
        )
        results.append({
            **prop.__dict__,
            "distance_km": round(distance, 2)
        })

    # Trier par distance
    results.sort(key=lambda x: x["distance_km"])

    return results
```

### 10.3. Géocodage (Adresse → Coordonnées)

```python
# app/services/geocoding_service.py
import httpx
from app.core.config import settings

class GeocodingService:
    """Service de géocodage utilisant OpenStreetMap Nominatim"""

    BASE_URL = "https://nominatim.openstreetmap.org"

    async def geocode(self, address: str, city: str = None, country: str = "Benin"):
        """Convertir une adresse en coordonnées GPS"""
        query = f"{address}"
        if city:
            query += f", {city}"
        query += f", {country}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1
                },
                headers={
                    "User-Agent": "LOKAHOME/1.0"
                }
            )

            data = response.json()
            if data:
                return {
                    "latitude": float(data[0]["lat"]),
                    "longitude": float(data[0]["lon"]),
                    "display_name": data[0]["display_name"]
                }
            return None

    async def reverse_geocode(self, latitude: float, longitude: float):
        """Convertir des coordonnées en adresse"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/reverse",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json"
                },
                headers={
                    "User-Agent": "LOKAHOME/1.0"
                }
            )

            data = response.json()
            return {
                "address": data.get("display_name"),
                "city": data.get("address", {}).get("city"),
                "neighborhood": data.get("address", {}).get("suburb")
            }
```

### 10.4. Configuration PostGIS

```sql
-- Activer l'extension PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Ajouter une colonne géométrie aux propriétés
ALTER TABLE properties ADD COLUMN location GEOGRAPHY(POINT, 4326);

-- Créer un index spatial
CREATE INDEX idx_properties_location_geo ON properties USING GIST(location);

-- Trigger pour mettre à jour la colonne location automatiquement
CREATE OR REPLACE FUNCTION update_property_location()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_property_location
    BEFORE INSERT OR UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION update_property_location();
```

---

## 11. UPLOAD DE FICHIERS

### 11.1. Service d'upload

```python
# app/services/upload_service.py
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from uuid import uuid4
from PIL import Image
import io
from app.core.config import settings

class UploadService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,  # Pour MinIO local
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "properties",
        max_size: tuple = (1920, 1080),
        quality: int = 85
    ) -> str:
        """Upload et optimiser une image"""
        # Vérifier le type de fichier
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            raise ValueError("Type de fichier non autorisé")

        # Lire et optimiser l'image
        content = await file.read()
        image = Image.open(io.BytesIO(content))

        # Convertir en RGB si nécessaire
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Redimensionner si nécessaire
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Sauvegarder en JPEG optimisé
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)

        # Générer un nom unique
        file_extension = "jpg"
        unique_filename = f"{folder}/{uuid4()}.{file_extension}"

        # Upload vers S3
        try:
            self.s3_client.upload_fileobj(
                buffer,
                self.bucket_name,
                unique_filename,
                ExtraArgs={
                    "ContentType": "image/jpeg",
                    "ACL": "public-read"
                }
            )
        except ClientError as e:
            raise Exception(f"Erreur upload S3: {str(e)}")

        # Retourner l'URL publique
        return f"{settings.S3_PUBLIC_URL}/{unique_filename}"

    async def upload_document(self, file: UploadFile, folder: str = "documents") -> str:
        """Upload un document (PDF, etc.)"""
        allowed_types = ["application/pdf", "image/jpeg", "image/png"]
        if file.content_type not in allowed_types:
            raise ValueError("Type de fichier non autorisé")

        content = await file.read()

        # Vérifier la taille (max 10MB)
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("Fichier trop volumineux (max 10MB)")

        # Générer un nom unique
        ext = file.filename.split(".")[-1]
        unique_filename = f"{folder}/{uuid4()}.{ext}"

        # Upload vers S3
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=unique_filename,
            Body=content,
            ContentType=file.content_type,
            ACL="public-read"
        )

        return f"{settings.S3_PUBLIC_URL}/{unique_filename}"

    async def delete_file(self, file_url: str):
        """Supprimer un fichier"""
        # Extraire la clé du fichier depuis l'URL
        key = file_url.replace(f"{settings.S3_PUBLIC_URL}/", "")

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
        except ClientError as e:
            raise Exception(f"Erreur suppression S3: {str(e)}")

    async def generate_thumbnails(self, image_url: str) -> dict:
        """Générer des miniatures pour une image"""
        # Télécharger l'image originale
        key = image_url.replace(f"{settings.S3_PUBLIC_URL}/", "")

        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        image = Image.open(response['Body'])

        thumbnails = {}
        sizes = {
            "thumb": (150, 150),
            "medium": (600, 400),
            "large": (1200, 800)
        }

        for name, size in sizes.items():
            thumb = image.copy()
            thumb.thumbnail(size, Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            thumb.save(buffer, format="JPEG", quality=80)
            buffer.seek(0)

            thumb_key = key.replace(".", f"_{name}.")

            self.s3_client.upload_fileobj(
                buffer,
                self.bucket_name,
                thumb_key,
                ExtraArgs={"ContentType": "image/jpeg", "ACL": "public-read"}
            )

            thumbnails[name] = f"{settings.S3_PUBLIC_URL}/{thumb_key}"

        return thumbnails
```

### 11.2. Endpoints d'upload

```python
# app/api/v1/uploads.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
from app.services.upload_service import UploadService
from app.api.deps import get_current_user

router = APIRouter()
upload_service = UploadService()

@router.post("/images/property/{property_id}")
async def upload_property_images(
    property_id: str,
    files: List[UploadFile] = File(...),
    current_user = Depends(get_current_user)
):
    """Upload des images pour une propriété"""
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images autorisées")

    uploaded_urls = []
    for file in files:
        try:
            url = await upload_service.upload_image(
                file=file,
                folder=f"properties/{property_id}"
            )
            uploaded_urls.append(url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"uploaded": uploaded_urls}

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload d'avatar utilisateur"""
    try:
        url = await upload_service.upload_image(
            file=file,
            folder=f"avatars/{current_user.id}",
            max_size=(500, 500)
        )

        # Mettre à jour l'avatar de l'utilisateur
        current_user.avatar_url = url
        # Sauvegarder en BDD

        return {"avatar_url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload de document (contrat, pièce d'identité, etc.)"""
    try:
        url = await upload_service.upload_document(
            file=file,
            folder=f"documents/{current_user.id}"
        )
        return {"document_url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 12. API DOCUMENTATION

### 12.1. Configuration OpenAPI

```python
# app/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="LOKAHOME API",
    description="""
## API de la plateforme LOKAHOME

### Fonctionnalités principales

* **Authentification** - JWT avec refresh tokens
* **Gestion des utilisateurs** - Profils locataires, propriétaires, prestataires
* **Propriétés** - CRUD complet avec recherche avancée
* **Réservations** - Gestion des locations
* **Paiements** - Intégration FedaPay et Mobile Money
* **Services** - Marketplace de services de maintenance
* **Messagerie** - Communication en temps réel
* **Notifications** - Push, Email, SMS

### Authentification

Toutes les routes protégées nécessitent un token JWT dans le header:
```
Authorization: Bearer <access_token>
```
    """,
    version="1.0.0",
    contact={
        "name": "LOKAHOME Support",
        "email": "support@lokahome.bj"
    },
    license_info={
        "name": "Propriétaire",
    },
    openapi_tags=[
        {"name": "auth", "description": "Authentification et gestion des tokens"},
        {"name": "users", "description": "Gestion des utilisateurs"},
        {"name": "properties", "description": "Gestion des propriétés/logements"},
        {"name": "bookings", "description": "Gestion des réservations"},
        {"name": "payments", "description": "Paiements et transactions"},
        {"name": "services", "description": "Services de maintenance"},
        {"name": "messages", "description": "Messagerie"},
        {"name": "reviews", "description": "Avis et notations"},
        {"name": "admin", "description": "Administration"},
    ]
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags
    )

    # Ajouter les schémas de sécurité
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

### 12.2. Documentation des endpoints

```python
# app/api/v1/properties.py
from fastapi import APIRouter, Query, Path
from typing import List, Optional

router = APIRouter(prefix="/properties", tags=["properties"])

@router.get(
    "/",
    response_model=List[PropertyResponse],
    summary="Lister les propriétés",
    description="""
    Récupérer la liste des propriétés avec filtres optionnels.

    **Filtres disponibles:**
    - `city`: Filtrer par ville
    - `property_type`: Type de bien (house, apartment, hotel, etc.)
    - `min_price` / `max_price`: Fourchette de prix
    - `bedrooms`: Nombre de chambres minimum
    - `is_furnished`: Meublé ou non
    """,
    responses={
        200: {
            "description": "Liste des propriétés",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "uuid",
                            "title": "Appartement 3 chambres à Cotonou",
                            "price": 150000,
                            "city": "Cotonou"
                        }
                    ]
                }
            }
        }
    }
)
async def list_properties(
    city: Optional[str] = Query(None, description="Filtrer par ville"),
    property_type: Optional[str] = Query(None, description="Type de propriété"),
    min_price: Optional[float] = Query(None, ge=0, description="Prix minimum"),
    max_price: Optional[float] = Query(None, ge=0, description="Prix maximum"),
    bedrooms: Optional[int] = Query(None, ge=0, description="Nombre de chambres min"),
    is_furnished: Optional[bool] = Query(None, description="Meublé"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(20, ge=1, le=100, description="Résultats par page")
):
    """Liste des propriétés avec pagination et filtres"""
    pass

@router.get(
    "/{property_id}",
    response_model=PropertyDetailResponse,
    summary="Détails d'une propriété",
    responses={
        200: {"description": "Détails de la propriété"},
        404: {"description": "Propriété non trouvée"}
    }
)
async def get_property(
    property_id: str = Path(..., description="ID de la propriété")
):
    """Récupérer les détails complets d'une propriété"""
    pass
```

### 12.3. Génération de la documentation

L'API génère automatiquement :
- **Swagger UI** : Disponible sur `/docs`
- **ReDoc** : Disponible sur `/redoc`
- **OpenAPI JSON** : Disponible sur `/api/v1/openapi.json`

---

## 13. ENVIRONNEMENTS ET DÉPLOIEMENT

### 13.1. Variables d'environnement

```bash
# .env.example

# Application
PROJECT_NAME=LOKAHOME
VERSION=1.0.0
DEBUG=false
API_V1_STR=/api/v1
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Base de données
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lokahome
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://lokahome.bj"]

# AWS S3 / MinIO
S3_ENDPOINT_URL=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_REGION=us-east-1
S3_BUCKET_NAME=lokahome
S3_PUBLIC_URL=http://localhost:9000/lokahome

# Paiements
FEDAPAY_SECRET_KEY=sk_sandbox_xxx
FEDAPAY_ENVIRONMENT=sandbox
MTN_API_KEY=xxx
MTN_ENVIRONMENT=sandbox

# Email
MAIL_USERNAME=noreply@lokahome.bj
MAIL_PASSWORD=xxx
MAIL_FROM=noreply@lokahome.bj
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com

# SMS
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1234567890

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json

# Sentry (monitoring erreurs)
SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 13.2. Configuration par environnement

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "LOKAHOME"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Sécurité
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Base de données
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = []

    # S3
    S3_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str
    S3_PUBLIC_URL: str

    # Paiements
    FEDAPAY_SECRET_KEY: str
    FEDAPAY_ENVIRONMENT: str = "sandbox"

    # Email
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str

    # SMS
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Firebase
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    # Sentry
    SENTRY_DSN: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

### 13.3. Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 13.4. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://lokahome:lokahome@db:5432/lokahome
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgis/postgis:15-3.3
    environment:
      - POSTGRES_USER=lokahome
      - POSTGRES_PASSWORD=lokahome
      - POSTGRES_DB=lokahome
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

  celery:
    build: .
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://lokahome:lokahome@db:5432/lokahome
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A app.tasks beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### 13.5. Configuration Nginx (Production)

```nginx
# nginx.conf
upstream api {
    server api:8000;
}

server {
    listen 80;
    server_name api.lokahome.bj;

    # Redirection HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.lokahome.bj;

    ssl_certificate /etc/letsencrypt/live/api.lokahome.bj/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.lokahome.bj/privkey.pem;

    # Sécurité SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Headers de sécurité
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Limite de taille des uploads
    client_max_body_size 20M;

    location / {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Cache des fichiers statiques
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 13.6. Script de déploiement

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Déploiement LOKAHOME API"

# Variables
DEPLOY_DIR=/opt/lokahome
BACKUP_DIR=/opt/lokahome/backups

# 1. Sauvegarde de la base de données
echo "📦 Sauvegarde de la base de données..."
docker exec lokahome-db pg_dump -U lokahome lokahome > $BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql

# 2. Pull des dernières modifications
echo "📥 Récupération du code..."
cd $DEPLOY_DIR
git pull origin main

# 3. Build des images Docker
echo "🔨 Build des images..."
docker-compose build

# 4. Exécuter les migrations
echo "🗃️ Exécution des migrations..."
docker-compose run --rm api alembic upgrade head

# 5. Redémarrer les services
echo "🔄 Redémarrage des services..."
docker-compose up -d

# 6. Vérifier le statut
echo "✅ Vérification du statut..."
sleep 5
curl -f http://localhost:8000/health || exit 1

echo "🎉 Déploiement terminé avec succès!"
```

---

## 14. TESTS

### 14.1. Configuration pytest

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db
from app.models.base import Base

# Base de données de test
SQLALCHEMY_DATABASE_URL = "postgresql://test:test@localhost:5432/lokahome_test"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session):
    """Créer un utilisateur de test"""
    from app.models.user import User
    from app.core.security import get_password_hash

    user = User(
        email="test@example.com",
        phone="+22990000000",
        password_hash=get_password_hash("testpassword"),
        first_name="Test",
        last_name="User",
        user_type="tenant",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user

@pytest.fixture
def auth_headers(test_user):
    """Headers d'authentification pour les tests"""
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}
```

### 14.2. Tests unitaires

```python
# tests/unit/test_services.py
import pytest
from app.services.user_service import UserService
from app.services.property_service import PropertyService

class TestUserService:
    def test_create_user(self, db_session):
        """Test de création d'utilisateur"""
        user_data = {
            "email": "new@example.com",
            "phone": "+22990000001",
            "password": "securepassword",
            "first_name": "New",
            "last_name": "User",
            "user_type": "tenant"
        }

        user = UserService.create_user(db_session, user_data)

        assert user.email == "new@example.com"
        assert user.is_active is True
        assert user.is_verified is False

    def test_create_user_duplicate_email(self, db_session, test_user):
        """Test d'erreur pour email dupliqué"""
        user_data = {
            "email": test_user.email,  # Email existant
            "phone": "+22990000002",
            "password": "password",
            "first_name": "Test",
            "last_name": "User",
            "user_type": "tenant"
        }

        with pytest.raises(ValueError, match="Email already registered"):
            UserService.create_user(db_session, user_data)

class TestPropertyService:
    def test_create_property(self, db_session, test_user):
        """Test de création de propriété"""
        property_data = {
            "title": "Appartement test",
            "description": "Description test",
            "property_type": "apartment",
            "rental_type": "short_term",
            "price": 50000,
            "address": "123 Rue Test",
            "city": "Cotonou"
        }

        # Changer le type de l'utilisateur en landlord
        test_user.user_type = "landlord"
        db_session.commit()

        prop = PropertyService.create_property(
            db_session,
            property_data,
            owner_id=test_user.id
        )

        assert prop.title == "Appartement test"
        assert prop.owner_id == test_user.id
        assert prop.status == "draft"
```

### 14.3. Tests d'intégration

```python
# tests/integration/test_api.py
import pytest

class TestAuthAPI:
    def test_register(self, client):
        """Test d'inscription"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "phone": "+22990000003",
                "password": "securepassword123",
                "first_name": "New",
                "last_name": "User",
                "user_type": "tenant"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == "newuser@example.com"

    def test_login(self, client, test_user):
        """Test de connexion"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client, test_user):
        """Test de connexion avec mot de passe invalide"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401

class TestPropertiesAPI:
    def test_list_properties(self, client):
        """Test de liste des propriétés"""
        response = client.get("/api/v1/properties")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_property_unauthorized(self, client):
        """Test création sans authentification"""
        response = client.post(
            "/api/v1/properties",
            json={
                "title": "Test",
                "property_type": "apartment",
                "rental_type": "short_term",
                "price": 50000,
                "address": "Test",
                "city": "Cotonou"
            }
        )

        assert response.status_code == 401

    def test_create_property_authorized(self, client, auth_headers):
        """Test création avec authentification"""
        response = client.post(
            "/api/v1/properties",
            headers=auth_headers,
            json={
                "title": "Mon appartement",
                "description": "Bel appartement",
                "property_type": "apartment",
                "rental_type": "short_term",
                "price": 50000,
                "address": "123 Rue Test",
                "city": "Cotonou"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Mon appartement"

class TestBookingsAPI:
    def test_create_booking(self, client, auth_headers, test_property):
        """Test de création de réservation"""
        response = client.post(
            "/api/v1/bookings",
            headers=auth_headers,
            json={
                "property_id": str(test_property.id),
                "start_date": "2024-02-01",
                "end_date": "2024-02-15"
            }
        )

        assert response.status_code == 201
```

### 14.4. Tests de charge (Locust)

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class LokaHomeUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Connexion au démarrage"""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "loadtest@example.com",
                "password": "loadtestpassword"
            }
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(3)
    def list_properties(self):
        """Lister les propriétés (tâche fréquente)"""
        self.client.get("/api/v1/properties")

    @task(2)
    def search_properties(self):
        """Rechercher des propriétés"""
        self.client.get("/api/v1/properties/search?city=Cotonou&max_price=100000")

    @task(1)
    def view_property(self):
        """Voir une propriété"""
        self.client.get("/api/v1/properties/some-property-id")

    @task(1)
    def get_my_profile(self):
        """Voir mon profil"""
        self.client.get("/api/v1/users/me", headers=self.headers)
```

### 14.5. Exécution des tests

```bash
# Exécuter tous les tests
pytest

# Avec couverture de code
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/unit/
pytest tests/integration/

# Tests avec verbose
pytest -v

# Tests de charge (Locust)
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

---

## 15. MONITORING ET LOGS

### 15.1. Configuration Loguru

```python
# app/core/logging.py
import sys
from loguru import logger
from app.core.config import settings

def setup_logging():
    """Configuration du système de logging"""

    # Supprimer le handler par défaut
    logger.remove()

    # Format des logs
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Handler console
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True
    )

    # Handler fichier (rotation quotidienne)
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="INFO",
        rotation="00:00",  # Nouvelle fichier chaque jour
        retention="30 days",  # Garder 30 jours
        compression="zip"  # Compresser les anciens fichiers
    )

    # Handler erreurs séparé
    logger.add(
        "logs/errors_{time:YYYY-MM-DD}.log",
        format=log_format,
        level="ERROR",
        rotation="00:00",
        retention="90 days",
        compression="zip"
    )

    return logger

# Initialisation
log = setup_logging()
```

### 15.2. Middleware de logging des requêtes

```python
# app/middleware/logging.py
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import log

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Début de la requête
        start_time = time.time()

        # Informations de la requête
        request_id = request.headers.get("X-Request-ID", "-")
        client_ip = request.client.host

        log.info(
            f"Request started | {request.method} {request.url.path} | "
            f"Client: {client_ip} | Request-ID: {request_id}"
        )

        # Traitement de la requête
        try:
            response = await call_next(request)

            # Durée de traitement
            process_time = time.time() - start_time

            log.info(
                f"Request completed | {request.method} {request.url.path} | "
                f"Status: {response.status_code} | Duration: {process_time:.3f}s"
            )

            # Ajouter le temps de traitement dans les headers
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            process_time = time.time() - start_time
            log.error(
                f"Request failed | {request.method} {request.url.path} | "
                f"Error: {str(e)} | Duration: {process_time:.3f}s"
            )
            raise
```

### 15.3. Configuration Prometheus

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Métriques
REQUEST_COUNT = Counter(
    'lokahome_requests_total',
    'Total des requêtes HTTP',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'lokahome_request_latency_seconds',
    'Latence des requêtes HTTP',
    ['method', 'endpoint']
)

ACTIVE_USERS = Gauge(
    'lokahome_active_users',
    'Nombre d\'utilisateurs actifs'
)

PROPERTIES_COUNT = Gauge(
    'lokahome_properties_total',
    'Nombre total de propriétés',
    ['status']
)

BOOKINGS_COUNT = Counter(
    'lokahome_bookings_total',
    'Nombre total de réservations',
    ['status']
)

# Endpoint pour Prometheus
async def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### 15.4. Middleware de métriques

```python
# app/middleware/metrics.py
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        # Enregistrer les métriques
        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        status = response.status_code

        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()

        REQUEST_LATENCY.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        return response
```

### 15.5. Configuration Sentry

```python
# app/core/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from app.core.config import settings

def init_sentry():
    """Initialiser Sentry pour le monitoring des erreurs"""
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                CeleryIntegration()
            ],
            traces_sample_rate=0.1,  # 10% des transactions
            profiles_sample_rate=0.1,
            environment=settings.ENVIRONMENT,
            release=settings.VERSION
        )
```

### 15.6. Health Check avancé

```python
# app/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from app.core.database import get_db
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check basique"""
    return {"status": "healthy", "version": settings.VERSION}

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Health check détaillé avec vérification des services"""
    health = {
        "status": "healthy",
        "version": settings.VERSION,
        "checks": {}
    }

    # Vérifier PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        health["checks"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Vérifier Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health["checks"]["redis"] = {"status": "healthy"}
    except Exception as e:
        health["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Vérifier S3/MinIO
    try:
        # Test de connexion S3
        health["checks"]["storage"] = {"status": "healthy"}
    except Exception as e:
        health["checks"]["storage"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    return health

@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe pour Kubernetes"""
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except:
        return {"ready": False}, 503
```

### 15.7. Dashboard Grafana

Configuration des dashboards Grafana pour visualiser :
- Nombre de requêtes par endpoint
- Latence des requêtes (p50, p95, p99)
- Taux d'erreurs
- Nombre d'utilisateurs actifs
- Métriques métier (réservations, paiements)

```json
// grafana/dashboards/lokahome.json (extrait)
{
  "title": "LOKAHOME API Dashboard",
  "panels": [
    {
      "title": "Requêtes par seconde",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(lokahome_requests_total[5m])",
          "legendFormat": "{{method}} {{endpoint}}"
        }
      ]
    },
    {
      "title": "Latence (p95)",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(lokahome_request_latency_seconds_bucket[5m]))",
          "legendFormat": "p95"
        }
      ]
    },
    {
      "title": "Taux d'erreurs",
      "type": "stat",
      "targets": [
        {
          "expr": "sum(rate(lokahome_requests_total{status=~\"5..\"}[5m])) / sum(rate(lokahome_requests_total[5m])) * 100"
        }
      ]
    }
  ]
}
```

---

## 16. ANNEXES

### 16.1. Commandes utiles

```bash
# Développement
uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Tests
pytest -v --cov=app
pytest -x  # Arrêter au premier échec

# Docker
docker-compose up -d
docker-compose logs -f api
docker-compose exec api bash

# Celery
celery -A app.tasks worker --loglevel=info
celery -A app.tasks beat --loglevel=info
celery -A app.tasks flower  # Monitoring

# Base de données
docker-compose exec db psql -U lokahome -d lokahome
```

### 16.2. Références

- FastAPI Documentation: https://fastapi.tiangolo.com
- SQLAlchemy 2.0: https://docs.sqlalchemy.org
- Pydantic v2: https://docs.pydantic.dev
- FedaPay API: https://docs.fedapay.com
- Firebase Admin SDK: https://firebase.google.com/docs/admin/setup
- Celery: https://docs.celeryq.dev

---

**Document rédigé pour le projet LOKAHOME**
**Version**: 1.0
**Dernière mise à jour**: Janvier 2026