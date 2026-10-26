# Seat · Backend

**Branch:** `seat/backend`

## Owns

- Auth (JWT, bcrypt), roles farmer / advisor
- PostGIS models + Alembic migrations
- REST under `/api/v1`
- Orchestrator + validator
- Docker Compose, Redis queue hook

## First MVP tasks

1. [ ] Compose: API + PostGIS + Redis healthy
2. [ ] Models: Farmer, Plot, Recommendation
3. [ ] `POST /auth/register`, `POST /auth/login`
4. [ ] `POST /plots` (GeoJSON), `GET /plots`
5. [ ] Orchestrator calls weather → satellite → agronomy → validator → explain → notify (stubs OK)
6. [ ] Validator: `show_dose` / `needs_check`
7. [ ] Seed plot `MA-001`

## Do not

- Hard-code doses in the API responses
- Call Ollama or Copernicus from core — use service modules owned by other seats
