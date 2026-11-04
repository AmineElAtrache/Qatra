# Seat · Backend

**Branch:** `seat/backend`

## Owns

- Auth (JWT, bcrypt), roles farmer / advisor, auth rate limit
- Models + Alembic migrations (`farmers`, `plots`, `recommendations`, `messages`)
- REST under `/api/v1`
- Orchestrator + validator (passes plot GeoJSON to Satellite)
- Docker Compose, Redis daily queue + worker
- Seed `MA-001`

## First MVP tasks

1. [x] Compose: API + Postgres/Redis healthy (`POSTGRES_IMAGE` optional for PostGIS)
2. [x] Models: Farmer, Plot, Recommendation, Message
3. [x] `POST /auth/register`, `POST /auth/login` (rate-limited)
4. [x] `POST /plots` (GeoJSON), `GET /plots`, `GET /plots/{id}`
5. [x] Orchestrator calls weather → satellite(geojson) → agronomy → validator → explain → notify
6. [x] Validator: `show_dose` / `needs_check`
7. [x] Seed plot `MA-001` + farmer/advisor demo accounts
8. [x] Alembic `0001_initial`
9. [x] Daily worker: `python -m app.workers.daily --once` / `POST /api/v1/jobs/daily`

## Demo accounts

| Email | Password | Role |
| --- | --- | --- |
| farmer@example.com | demo-demo | farmer |
| advisor@example.com | demo-demo | advisor |

## Do not

- Hard-code doses in the API responses
- Call Ollama or Copernicus/GEE from core — use service modules owned by other seats
