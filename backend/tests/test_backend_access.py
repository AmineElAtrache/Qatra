"""Exercise ownership, advisor assignment, and daily-job scoping over HTTP."""
import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.geo import default_ma001_geojson, geojson_to_text
from app.core.security import create_access_token
from app.domain.models import Farmer, Plot, Recommendation
from app.main import app
from app.workers import daily
from app.api.v1 import ask, jobs, recommendations


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        users = [Farmer(email=f"{i}@test.example", password_hash="unused", role=role)
                 for i, role in enumerate(["farmer", "farmer", "advisor", "advisor"])]
        db.add_all(users)
        db.flush()
        db.add_all([
            Plot(public_id="MA-001", owner_id=users[0].id, advisor_id=users[2].id,
                 geom=geojson_to_text(default_ma001_geojson())),
            Plot(public_id="PRIVATE", owner_id=users[1].id, advisor_id=users[3].id),
        ])
        db.commit()
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(daily, "SessionLocal", factory)
    with TestClient(app) as client:
        yield client, users, factory
    app.dependency_overrides.clear()
    engine.dispose()


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def test_advisors_only_see_linked_plots(setup):
    client, users, _ = setup
    response = client.get("/api/v1/advisor/plots", headers=headers(users[2]))
    assert response.status_code == 200
    assert [p["public_id"] for p in response.json()] == ["MA-001"]
    assert client.get("/api/v1/advisor/plots", headers=headers(users[0])).status_code == 403


def test_owner_controls_assignment_and_private_routes(setup):
    client, users, _ = setup
    route = "/api/v1/plots/MA-001/advisor"
    assert client.put(route, json={"advisor_id": users[3].id}, headers=headers(users[1])).status_code == 404
    assert client.put(route, json={"advisor_id": users[1].id}, headers=headers(users[0])).status_code == 422
    assert client.put(route, json={"advisor_id": users[3].id}, headers=headers(users[0])).status_code == 200
    assert client.get("/api/v1/advisor/plots", headers=headers(users[2])).json() == []
    assert client.get("/api/v1/plots/PRIVATE", headers=headers(users[0])).status_code == 404
    assert client.get("/api/v1/plots/PRIVATE/recommendations", headers=headers(users[0])).status_code == 404
    assert client.post("/api/v1/plots/PRIVATE/recommendation", headers=headers(users[0])).status_code == 404


def test_daily_endpoint_passes_authenticated_scope(setup, monkeypatch):
    client, users, _ = setup
    run = AsyncMock(return_value={"enqueued": 1, "processed": 1, "remaining": 0})
    monkeypatch.setattr(jobs, "run_once", run)
    assert client.post("/api/v1/jobs/daily").status_code == 401
    assert client.post("/api/v1/jobs/daily", headers=headers(users[0])).status_code == 200
    assert run.call_args.kwargs["user"].id == users[0].id


def test_plot_creation_requires_valid_geometry(setup):
    client, users, _ = setup
    route = "/api/v1/plots"
    for geometry in [None, {"type": "Point", "coordinates": [0, 0]},
                     {"type": "Polygon", "coordinates": [[]]}]:
        assert client.post(route, json={"public_id": "NEW", "geojson": geometry},
                           headers=headers(users[0])).status_code == 422
    assert client.post(route, json={"public_id": "NEW", "geojson": default_ma001_geojson()},
                       headers=headers(users[0])).status_code == 200


def test_scoped_enqueue_and_persistence(setup, monkeypatch):
    _, users, factory = setup
    queued = []
    monkeypatch.setattr(daily, "enqueue_many", lambda ids, queue: queued.extend(ids) or len(ids))
    assert daily.enqueue_all_plots("test", users[2]) == 1
    assert queued == ["MA-001"]
    async def recommendation(**kwargs):
        assert kwargs["geojson"] == default_ma001_geojson()
        return {"engine_version": "test", "status": "needs_check", "texts": {}}
    monkeypatch.setattr(daily, "run_recommendation", recommendation)
    assert asyncio.run(daily.process_one("PRIVATE", user=users[0])) is None
    asyncio.run(daily.process_one("MA-001", user=users[0]))
    with factory() as db:
        assert db.query(Recommendation).count() == 1


def test_queue_continues_after_failure(monkeypatch):
    items = iter(["bad", "good", "deleted", None])
    monkeypatch.setattr(daily, "pop_plot", lambda **kwargs: next(items))
    async def process(public_id, **kwargs):
        if public_id == "bad":
            raise RuntimeError("service unavailable")
        return {} if public_id == "good" else None
    monkeypatch.setattr(daily, "process_one", process)
    assert asyncio.run(daily.drain_queue()) == {"processed": 1, "failed": ["bad"], "skipped": 1}


def test_manual_recommendation_passes_polygon_and_stores_row(setup, monkeypatch):
    client, users, factory = setup
    async def run(**kwargs):
        assert kwargs["geojson"] == default_ma001_geojson()
        return {"engine_version": "test", "status": "needs_check", "texts": {}}
    monkeypatch.setattr(recommendations, "run_recommendation", run)
    response = client.post("/api/v1/plots/MA-001/recommendation", headers=headers(users[0]))
    assert response.status_code == 200
    with factory() as db:
        assert db.query(Recommendation).one().payload["status"] == "needs_check"


def test_ask_uses_authorized_plot_payload_even_if_snapshot_changes(setup, monkeypatch):
    client, users, factory = setup
    payload = {"plot_id": "MA-001", "status": "needs_check"}
    with factory() as db:
        plot = db.query(Plot).filter(Plot.public_id == "MA-001").one()
        db.add(Recommendation(plot_id=plot.id, engine_version="test", status="needs_check", payload=payload))
        db.commit()
    monkeypatch.setattr(ask, "save_last_stored_state", lambda state: None)
    handler = AsyncMock(return_value={"answer": "Check the plot"})
    monkeypatch.setattr(ask, "ask_qatra", handler)
    response = client.post("/api/v1/plots/MA-001/ask", json={"question": "Water?"}, headers=headers(users[0]))
    assert response.status_code == 200
    assert handler.call_args.kwargs["last_payload"] == payload
    assert client.post("/api/v1/plots/PRIVATE/ask", json={"question": "Water?"}, headers=headers(users[0])).status_code == 404
