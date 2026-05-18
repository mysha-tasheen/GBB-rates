# GBB Rates

Hotel rate aggregation and booking API with clean architecture (domain → application → infrastructure → API).

## Stack

- Django 5 + Django Ninja
- PostgreSQL, Redis, Celery
- Docker Compose for local development only

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- API docs: http://localhost:8000/api/docs
- Django admin: http://localhost:8000/admin/

Create a superuser (optional):

```bash
docker compose exec web python manage.py createsuperuser
```

## Project layout

| Layer | Role |
|-------|------|
| `domain/` | Pure Python entities, repository interfaces, pricing rules |
| `application/` | Use cases and orchestration services |
| `infrastructure/` | Django ORM, supplier adapters, HTTP clients, cache |
| `api/` | HTTP routers (Django Ninja only) |
| `config/` | Settings and dependency injection container |
| `workers/` | Celery background tasks |

## Local development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Start Postgres and Redis, then:
python manage.py migrate
python scripts/seed_suppliers.py
python main.py
```

## Example API calls

Search rates:

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Content-Type: application/json" \
  -d '{"hotel_id":"H123","check_in":"2026-06-01","check_out":"2026-06-05","guests":2}'
```

Prebook:

```bash
curl -X POST http://localhost:8000/api/bookings/prebook \
  -H "Content-Type: application/json" \
  -d '{"supplier":"nuitee","hotel_id":"H123","guest_name":"Jane Doe","external_rate_id":"nuitee-H123-std","total_amount":"112.00"}'
```
# GBB-rates
