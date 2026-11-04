"""Opt-in checks against an EMPTY, disposable PostgreSQL database and Redis.

QATRA_INTEGRATION=1 DATABASE_URL=... REDIS_URL=... pytest -q tests/test_backend_integration.py
Never point this test at a development or production database.
"""
import asyncio
import os
from unittest.mock import AsyncMock

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import SessionLocal, engine
from app.core.geo import default_ma001_geojson
from app.domain.models import Farmer, Plot, Recommendation
from app.workers import daily, seed_ma001

pytestmark = pytest.mark.skipif(os.getenv("QATRA_INTEGRATION") != "1", reason="requires disposable PostgreSQL and Redis")


def test_clean_migrations_seed_daily_and_downgrade(monkeypatch):
    assert not inspect(engine).get_table_names(), "Use an empty disposable database"
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
    seed_ma001.main()
    seed_ma001.main()
    with SessionLocal() as db:
        assert db.query(Farmer).count() == 2
        plot = db.query(Plot).one()
        assert plot.advisor_id is not None
    async def recommendation(**kwargs):
        assert kwargs["geojson"] == default_ma001_geojson()
        return {"engine_version": "integration", "status": "needs_check", "texts": {"fr": "Check"}}
    monkeypatch.setattr(daily, "run_recommendation", recommendation)
    monkeypatch.setattr(daily.notification, "notify_farmer", AsyncMock(return_value={"channel": "web", "delivered": False}))
    result = asyncio.run(daily.run_once())
    assert result == {"enqueued": 1, "processed": 1, "failed": [], "skipped": 0, "remaining": 0}
    with SessionLocal() as db:
        assert db.query(Recommendation).count() == 1
    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    command.upgrade(config, "head")
