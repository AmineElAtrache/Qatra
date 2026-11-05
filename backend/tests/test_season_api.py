"""Agronomy seat, week 5 — season totals and fungal inputs through the API."""

import asyncio
from datetime import date, datetime, timezone

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
from app.services import orchestrator, season
from app.services.satellite_service import SatelliteObservation
from app.services.weather_service import WeatherObservation

TODAY = date(2026, 11, 4)


def _payload(etc, rain, dose, status="show_dose"):
    return {"etc_mm": etc, "effective_rain_mm": rain, "status": status, "display_dose": dose}


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        farmer = Farmer(email="f@test.example", password_hash="unused", role="farmer")
        advisor = Farmer(email="a@test.example", password_hash="unused", role="advisor")
        db.add_all([farmer, advisor])
        db.flush()
        plot = Plot(
            public_id="MA-001",
            owner_id=farmer.id,
            advisor_id=advisor.id,
            area_ha=1.2,
            geom=geojson_to_text(default_ma001_geojson()),
        )
        db.add(plot)
        db.flush()
        for stamp, body in [
            (datetime(2026, 8, 31, 9), _payload(50.0, 0.0, 50.0)),  # previous season
            (datetime(2026, 11, 1, 9), _payload(2.0, 0.0, 2.2)),
            (datetime(2026, 11, 2, 8), _payload(9.0, 0.0, 9.0)),  # replaced the same day
            (datetime(2026, 11, 2, 10), _payload(1.8, 1.5, 0.3)),
            (datetime(2026, 11, 3, 9), _payload(2.1, 0.0, 2.3)),
        ]:
            db.add(
                Recommendation(
                    plot_id=plot.id,
                    engine_version="0.1.0",
                    status=body["status"],
                    etc_mm=body["etc_mm"],
                    gross_irrigation_mm=body["display_dose"],
                    payload=body,
                    created_at=stamp,
                )
            )
        db.commit()
        ids = (farmer.id, advisor.id)

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(season, "today", lambda: TODAY)
    with TestClient(app) as client:
        yield client, ids, factory
    app.dependency_overrides.clear()
    engine.dispose()


def _auth(user_id):
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def test_advisor_sees_season_totals(setup):
    client, (_, advisor_id), _ = setup
    rows = client.get("/api/v1/advisor/plots", headers=_auth(advisor_id)).json()
    assert len(rows) == 1
    row = rows[0]
    assert row["season_start"] == "2026-09-01"
    assert row["season_days"] == 3
    assert row["season_etc_mm"] == 5.9
    assert row["season_rain_mm"] == 1.5
    assert row["season_water_mm"] == 4.8
    assert row["season_water_m3"] == 57.6


def _fake_weather_and_sat(monkeypatch):
    async def fake_weather(lat, lon):
        return WeatherObservation(
            temperature_c=20.0,
            humidity_pct=88.0,
            wind_kmh=9.0,
            rain_mm=5.0,
            radiation_mj=22.0,
            et0_mm_day=4.2,
            et0_source="test",
            observed_at=datetime.now(timezone.utc).isoformat(),
            quality="test",
        )

    async def fake_sat(*args, **kwargs):
        return SatelliteObservation(0.68, 0.21, date.today().isoformat(), 86.0, "sentinel-2", "test")

    async def fake_explain(payload):
        return {"fr": "ok", "darija": "ok", "ar": "ok"}

    monkeypatch.setattr(orchestrator.weather_service, "fetch_weather", fake_weather)
    monkeypatch.setattr(orchestrator.satellite_service, "fetch_indices", fake_sat)
    monkeypatch.setattr(orchestrator.explain, "explain", fake_explain)


def test_recommendation_response_has_season_but_stored_payload_does_not(setup, monkeypatch):
    client, (farmer_id, _), factory = setup
    _fake_weather_and_sat(monkeypatch)
    monkeypatch.setattr(season, "today", lambda: datetime.now(timezone.utc).date())
    out = client.post("/api/v1/plots/MA-001/recommendation", headers=_auth(farmer_id)).json()
    rec = out["recommendation"]
    assert rec["season"]["season_start"].endswith("-09-01")
    assert rec["season"]["days_counted"] >= 1
    with factory() as db:
        stored = db.get(Recommendation, out["id"]).payload
    assert "season" not in stored


def test_orchestrator_passes_humidity_so_fungal_risk_is_explained(monkeypatch):
    _fake_weather_and_sat(monkeypatch)
    kwargs = dict(
        plot_id="MA-001",
        crop="citrus",
        stage="fruit_growth",
        irrigation_method="drip",
        area_ha=1.2,
        geojson=default_ma001_geojson(),
    )
    first = asyncio.run(orchestrator.run_recommendation(**kwargs))
    assert first["humidity_pct"] == 88.0
    assert first["temperature_c"] == 20.0
    assert first["fungal_risk"] == "high"
    assert first["fungal_factors"] == ["humid_air", "mild_temperature", "rain_wets_leaves"]
    assert first["etc_mm"] == 3.15

    second = asyncio.run(orchestrator.run_recommendation(**kwargs))
    for key in ("etc_mm", "gross_irrigation_mm", "display_dose", "status", "fungal_risk", "reasons"):
        assert first[key] == second[key]
