"""Satellite seat tests; all tests are offline and use injected adapters."""

import asyncio
from datetime import date
from pathlib import Path

from app.services import satellite_service as sat


PLOT = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-7.5898, 33.5731], [-7.5888, 33.5731], [-7.5888, 33.5740], [-7.5898, 33.5740], [-7.5898, 33.5731]]],
    },
}


class FakeClient:
    def __init__(self, observation):
        self.observation = observation
        self.calls = []

    def observe(self, geometry, start, end):
        self.calls.append((geometry, start, end))
        return self.observation


def run(coro):
    return asyncio.run(coro)


def test_valid_and_invalid_geojson():
    assert sat.validate_polygon(PLOT).geom_type == "Polygon"
    result = run(sat.fetch_indices(geojson={"type": "Point", "coordinates": [0, 0]}))
    assert result.ndvi is None
    assert result.reason == "geojson_must_be_a_valid_polygon"


def test_ndvi_ndwi_use_scaled_surface_reflectance():
    ndvi, ndwi = sat.compute_indices(2000, 6000, 3000)
    assert ndvi == 0.5
    assert ndwi == 0.333333


def test_valid_pixel_percentage_and_scl_quality_threshold():
    assert sat.is_valid_scl(4) is True
    assert sat.is_valid_scl(3) is False
    assert sat.is_valid_scl(9) is False
    assert sat.valid_pixel_percentage(70, 100) == 70.0
    assert sat.valid_pixel_percentage(69, 100) == 69.0
    client = FakeClient(sat.SatelliteObservation(0.5, 0.2, "2026-10-20", 69, "sentinel-2", "low_valid_pixels"))
    result = run(sat.fetch_indices(geojson=PLOT, client=client))
    assert result.ndvi is None
    assert result.ndwi is None
    assert result.radar_fallback is False
    assert result.valid_pixel_pct == 69
    assert result.quality == "low_valid_pixels"


def test_exactly_70_percent_keeps_optical_indices_without_radar_call():
    client = FakeClient(sat.SatelliteObservation(0.5, 0.2, "2026-10-20", 70, "sentinel-2", "good"))
    radar_client = FakeClient(sat.SatelliteObservation(None, None, "2026-10-21", None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=client, radar_client=radar_client))
    assert result.ndvi == 0.5
    assert result.radar_fallback is False
    assert radar_client.calls == []


def test_sentinel1_is_used_only_when_a_scene_exists(monkeypatch):
    optical = sat.SatelliteObservation(None, None, None, 20, "sentinel-2", "low_valid_pixels")
    radar = sat.SatelliteObservation(None, None, "2026-10-19", None, "sentinel-1", "radar_fallback")
    assert sat.maybe_sentinel1_fallback(optical, radar).radar_fallback is True
    assert sat.maybe_sentinel1_fallback(optical).satellite_source == "sentinel-2"
    result = run(sat.fetch_indices(geojson=PLOT, client=FakeClient(optical), radar_client=FakeClient(radar)))
    assert result.radar_fallback is True
    assert result.satellite_source == "sentinel-1"
    assert result.ndvi is None
    monkeypatch.setattr(sat, "_observe_sentinel1", lambda *args: None)
    result = run(sat.fetch_indices(geojson=PLOT, client=FakeClient(optical)))
    assert result.radar_fallback is False
    assert result.ndvi is None
    assert result.reason == "no_sentinel1_scene"


def test_offline_scene_preserves_real_date_and_contract_fields():
    fixture_dir = Path(__file__).parent / "fixtures"
    result = run(sat.fetch_indices(geojson=PLOT, offline_dir=fixture_dir))
    assert result.ndvi_observed_at == "2025-06-01"
    assert result.quality == "offline"
    assert result.to_contract_dict() == {
        "ndvi": 0.61,
        "ndwi": 0.18,
        "ndvi_observed_at": "2025-06-01",
        "valid_pixel_pct": 88.0,
        "satellite_source": "sentinel-2",
    }


def test_earth_engine_failure_is_controlled(monkeypatch):
    def fail(*args):
        raise sat.EarthEngineUnavailable("auth_failed")

    monkeypatch.setattr(sat, "_observe_earth_engine", fail)
    monkeypatch.setattr(sat, "_observe_sentinel1", lambda *args: None)
    result = run(sat.fetch_indices(geojson=PLOT))
    assert result.ndvi is None
    assert result.ndwi is None
    assert result.reason == "auth_failed"


def test_observation_window_is_forwarded():
    client = FakeClient(sat.sample_optical())
    run(sat.fetch_indices(geojson=PLOT, analysis_date=date(2026, 10, 20), client=client))
    _, start, end = client.calls[0]
    assert start.isoformat() == "2026-10-10"
    assert end.isoformat() == "2026-10-20"
