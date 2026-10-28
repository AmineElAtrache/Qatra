"""Integration coverage for the daily recommendation pipeline."""

import asyncio
from datetime import date, datetime, timezone

from app.services import orchestrator
from app.services.satellite_service import SatelliteObservation
from app.services.weather_service import WeatherObservation


def test_daily_recommendation_pipeline(monkeypatch):
    async def fake_weather(lat, lon):
        return WeatherObservation(
            temperature_c=28.0,
            humidity_pct=45.0,
            wind_kmh=9.0,
            rain_mm=1.5,
            radiation_mj=22.0,
            et0_mm_day=4.2,
            et0_source="test",
            observed_at=datetime.now(timezone.utc).isoformat(),
            quality="test",
        )

    async def fake_satellite(bbox=None):
        return SatelliteObservation(
            ndvi=0.68,
            ndwi=0.21,
            ndvi_observed_at=date.today().isoformat(),
            valid_pixel_pct=86.0,
            satellite_source="test",
            quality="test",
        )

    async def fake_explanation(payload):
        return {"fr": "Recommendation ready", "ar": "جاهز", "darija": "Wajed"}

    monkeypatch.setattr(orchestrator.weather_service, "fetch_weather", fake_weather)
    monkeypatch.setattr(orchestrator.satellite_service, "fetch_indices", fake_satellite)
    monkeypatch.setattr(orchestrator.explain, "explain", fake_explanation)

    result = asyncio.run(
        orchestrator.run_recommendation(
            plot_id="MA-001",
            crop="citrus",
            stage="fruit_growth",
            irrigation_method="drip",
            area_ha=1.2,
        )
    )

    assert result["status"] == "show_dose"
    assert result["etc_mm"] == 3.15
    assert result["display_dose"] == result["gross_irrigation_mm"]
    assert result["texts"]["fr"] == "Recommendation ready"