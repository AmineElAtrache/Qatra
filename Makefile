.PHONY: up down build logs api-test web-install migrate seed worker contract help

help:
	@echo "Qatra shortcuts"
	@echo "  make up           Start db, Redis, API, web"
	@echo "  make down         Stop stack"
	@echo "  make api-test     Run backend pytest"
	@echo "  make web-install  Install Next.js deps"
	@echo "  make migrate      Run Alembic migrations"
	@echo "  make seed         Load sample plot MA-001 + roles"
	@echo "  make worker       Run daily job once (enqueue + drain)"
	@echo "  make contract     Show shared JSON contract path"

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f api web

api-test:
	cd backend && python -m pytest -q

web-install:
	cd web && npm install

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.workers.seed_ma001

worker:
	cd backend && python -m app.workers.daily --once

contract:
	@echo docs/contract.json
