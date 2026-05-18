# GBB Rates

## Project layout

```
backend/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── config/
├── apps/
│   ├── core/          # Pure Python (domain, adapters, services, repository)
│   └── api/           # Django Ninja (v1/schemas, v1/endpoints)
├── static/
├── media/
└── templates/
```

## Docker (local dev)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Or from `backend/`:

```bash
cd backend && cp .env.example .env && docker compose up --build
```
