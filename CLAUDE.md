# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Always use Context7 MCP tools when code generation, setup/installation steps, or library/API documentation is needed.

## Project Overview

LOKAHOME is a rental property platform for Benin with an integrated service marketplace.

## Development Commands

```bash
# Quick start (recommended)
./start.sh dev                         # Start in development mode
./start.sh install                     # First-time setup (venv + deps)
./start.sh docker                      # Start with Docker Compose

# Alternative manual commands
uvicorn app.main:app --reload --port 8000

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head

# Run tests
pytest -v --cov=app                    # All tests with coverage
pytest tests/unit/test_auth.py -v      # Single test file
pytest -k "test_login" -v              # Run tests matching pattern
pytest -m "not slow" -v                # Skip slow tests

# Linting and formatting
ruff check app --fix                   # Lint and auto-fix with ruff
black app tests                        # Format code
isort app tests                        # Sort imports
mypy app                               # Type checking

# Docker environment
docker-compose up -d                   # Start all services
docker-compose logs -f api             # Follow API logs
docker-compose exec db psql -U lokahome -d lokahome  # Database shell

# Celery workers
celery -A app.tasks worker --loglevel=info
celery -A app.tasks beat --loglevel=info
```

## Architecture

Clean Architecture with strict layering - dependencies flow inward only:

```
Endpoints (api/) → Services (services/) → Repositories (repositories/) → Models (models/)
     ↓                    ↓                        ↓
  Schemas            Business Logic           Data Access
```

### Data Flow Pattern

1. **Request** → `api/v1/endpoints/` validates with Pydantic schemas
2. **Service** → `services/` contains business logic, orchestrates repositories
3. **Repository** → `repositories/` handles all database operations via `BaseRepository`
4. **Model** → `models/` SQLAlchemy models inherit from `BaseModel` (UUID + timestamps)

### Dependency Injection

Use type aliases from `app/api/deps.py`:
- `DbSession` - async SQLAlchemy session
- `CurrentUser`, `ActiveUser`, `VerifiedUser` - authenticated user dependencies
- `RequireTenant`, `RequireLandlord`, `RequireProvider`, `RequireAdmin` - role guards

### Models

All models inherit from `BaseModel` which provides:
- `id`: UUID primary key (auto-generated)
- `created_at`, `updated_at`: timestamps with timezone

### Repositories

Extend `BaseRepository[ModelType]` for CRUD. Methods available:
- `get(id)`, `get_by_field(field, value)`, `get_multi(skip, limit, filters, order_by)`
- `create(data)`, `update(instance, data)`, `delete(instance)`
- `exists(id)`, `exists_by_field(field, value)`, `count(filters)`

## Testing

Tests use pytest-asyncio with fixtures in `tests/conftest.py`:
- `db_session` - fresh database session per test (auto-rollback)
- `client` - async HTTP client with dependency overrides
- `test_user`, `test_landlord`, `test_admin` - pre-created user fixtures
- `auth_headers`, `landlord_auth_headers`, `admin_auth_headers` - JWT auth headers

Test database: `lokahome_test` (created from main DB URL by replacing database name)

## Payment Providers

Three payment methods integrated:
1. **FedaPay** - Primary, redirect-based flow with webhook callbacks
2. **MTN MoMo** - Request-to-pay via USSD prompt
3. **Moov Money** - Similar USSD-based flow

Webhooks are handled at `/api/v1/payments/webhook/{provider}`.

## Key Configuration

Settings loaded via Pydantic from environment (see `.env.example`):
- `DATABASE_URL` - PostgreSQL connection string (asyncpg driver)
- `REDIS_URL` - Redis for cache and Celery broker
- `SECRET_KEY` - JWT signing key
- `SUPERADMIN_*` - Super admin credentials (created automatically at startup)
- `FEDAPAY_*` - Payment provider credentials

## Important Naming Conventions

SQLAlchemy reserved names to avoid in models:
- `metadata` - Use `extra_data` instead for JSON fields
- `property` - Use `booked_property` for Booking→Property relationship (conflicts with Python's `@property` decorator)

## Documentation

- `/docs/document-_technique.md` - Complete technical specification
- `/docs/toitplus_objectif_info.md` - Business objectives and roadmap
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
