"""Interface seat, week 5 — in-app notifications and advisor plot geometry."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.geo import default_ma001_geojson, geojson_to_text
from app.core.security import create_access_token
from app.domain.models import Farmer, Message, Plot
from app.main import app


@pytest.fixture
def setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        farmer = Farmer(email="f@test.example", password_hash="x", role="farmer")
        other = Farmer(email="o@test.example", password_hash="x", role="farmer")
        advisor = Farmer(email="a@test.example", password_hash="x", role="advisor")
        db.add_all([farmer, other, advisor])
        db.flush()
        plot = Plot(public_id="MA-001", owner_id=farmer.id, advisor_id=advisor.id,
                    geom=geojson_to_text(default_ma001_geojson()))
        db.add(plot)
        db.flush()
        db.add_all([
            Message(farmer_id=farmer.id, plot_id=plot.id, channel="web", direction="outbound",
                    body="Besoin à vérifier.", status="queued"),
            Message(farmer_id=other.id, channel="web", direction="outbound", body="Pas pour toi", status="queued"),
            Message(farmer_id=farmer.id, channel="telegram", direction="inbound", body="question", status="received"),
        ])
        db.commit()
        ids = (farmer.id, other.id, advisor.id)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client, ids
    app.dependency_overrides.clear()
    engine.dispose()


def _auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def test_user_sees_only_own_outbound_notifications(setup):
    client, (farmer_id, _, _) = setup
    rows = client.get("/api/v1/notifications", headers=_auth(farmer_id)).json()
    assert [r["body"] for r in rows] == ["Besoin à vérifier."]
    assert rows[0]["plot_id"] == "MA-001"


def test_notifications_need_login(setup):
    client, _ = setup
    assert client.get("/api/v1/notifications").status_code == 401


def test_test_notification_is_stored_and_listed(setup):
    client, (farmer_id, _, _) = setup
    sent = client.post("/api/v1/notifications/test", headers=_auth(farmer_id))
    assert sent.status_code == 200
    body = sent.json()
    assert body["channel"] == "web"  # no Telegram token in tests → in-app
    assert body["body"].startswith("Test Qatra")
    rows = client.get("/api/v1/notifications", headers=_auth(farmer_id)).json()
    assert rows[0]["id"] == body["id"]


def test_advisor_plots_carry_geometry_for_the_map(setup):
    client, (_, _, advisor_id) = setup
    rows = client.get("/api/v1/advisor/plots", headers=_auth(advisor_id)).json()
    assert rows[0]["public_id"] == "MA-001"
    assert rows[0]["geojson"]["geometry"]["type"] == "Polygon"
