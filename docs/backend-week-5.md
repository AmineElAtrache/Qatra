# Backend Week 5

## Start and verify

Run `docker compose up --build -d`. The API runs `alembic upgrade head` before
starting; the optional worker waits for API health. Seeding is explicit:

```sh
make seed
make worker
docker compose --profile worker up -d worker
```

On Windows without Make, use `docker compose exec api python -m app.workers.seed_ma001`
and `docker compose exec api python -m app.workers.daily --once`.
The seed is repeatable and links the demo advisor to MA-001. It refuses to take
MA-001 from a different owner. Production workers never create tables or demo users.

The loop runs a pass on startup, then waits 86400 seconds between passes.
Use `--interval` to change that delay. Individual plot failures are logged and
returned in `failed`; other plots continue. A failed plot is retried on the next
pass. Redis locks prevent overlapping passes on the same queue for up to one hour.
This is a simple queue: a process crash after popping an item can lose that item
until the next pass, and separate user/global passes can recompute the same plot.

## Access and API

- Advisors see only plots with their `advisor_id`.
- The plot owner assigns or removes an advisor with
  `PUT /api/v1/plots/{public_id}/advisor`, body `{"advisor_id": 3}` or
  `{"advisor_id": null}`. The target must be an existing advisor account.
- `POST /api/v1/jobs/daily` processes only the caller's owned plots (farmer)
  or assigned plots (advisor). Its queue and status are scoped to that account.
- The CLI worker processes all plots. Empty databases are valid: zero enqueued.
- New plots require valid Polygon/MultiPolygon GeoJSON and a positive area.
- Missing geometry no longer substitutes MA-001. Missing imagery never gets
  replaced by a demo sample in the recommendation pipeline, even if an old
  `.env` still sets `SATELLITE_DEMO_FALLBACK=true`.
- Unknown stages/methods, missing ET0, invalid/future observation dates, and
  missing satellite quality prevent displaying a dose.

Existing response fields and `docs/contract.json` are unchanged.

## Database compatibility

PostgreSQL 16 is the default. Set `POSTGRES_IMAGE=postgis/postgis:16-3.4`
before starting a fresh database to use PostGIS. Plot geometry remains GeoJSON
text; no Geometry-column conversion is included.

For a legacy database created with `Base.metadata.create_all`, first back it up
and compare its schema with migration `0001_initial`. Only if they match, run
`alembic stamp 0001_initial`, then `alembic upgrade head`. Do not stamp an empty
or mismatched database. Existing unassigned plots remain invisible to advisors
until their owners assign them; the demo seed links MA-001.
Migration `0003_required_fields` aligns required columns with the ORM. If legacy
rows contain NULL in those columns, correct the source data before retrying;
the migration deliberately does not fill in invented values.

## Tests

From `backend`, run `python -m pytest -q`. HTTP regression tests use SQLite,
and external weather/satellite/explanation calls are mocked where needed.

For PostgreSQL migrations and a real Redis queue, use an **empty disposable**
database, set `QATRA_INTEGRATION=1`, `DATABASE_URL`, and `REDIS_URL`, then run:

```sh
python -m pytest -q tests/test_backend_integration.py
```

That opt-in test upgrades, seeds twice, stores a recommendation, downgrades,
and upgrades again. It must never target a development or production database.
