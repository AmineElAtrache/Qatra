"""Focused tests for the authenticated satellite overlay endpoint."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.plots import get_satellite_overlay
from app.core.config import settings
from app.core.geo import geojson_to_text
from app.services.satellite_service import _geometry_digest, _overlay_filename, validate_polygon


PLOT = {
    "type": "Feature",
    "properties": {},
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-7.5898, 33.5731], [-7.5888, 33.5731], [-7.5888, 33.574], [-7.5898, 33.574], [-7.5898, 33.5731]]],
    },
}


class Query:
    def __init__(self, value):
        self.value = value

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.value


class Database:
    def __init__(self, plot, recommendation):
        self.plot = plot
        self.recommendation = recommendation

    def query(self, model):
        return Query(self.plot if model.__name__ == "Plot" else self.recommendation)


class DeniedDatabase(Database):
    def query(self, model):
        return Query(None)


def _plot(public_id="MA-001"):
    return SimpleNamespace(id=7, public_id=public_id, owner_id=11, advisor_id=22, geom=geojson_to_text(PLOT))


def _recommendation(observed="2026-11-01"):
    return SimpleNamespace(
        payload={"ndvi_observed_at": observed, "satellite_source": "sentinel-2"},
        created_at="2026-11-04T00:00:00+00:00",
    )


def _write_overlay(plot_id="MA-001", observed="2026-11-01"):
    root = Path("artifacts")
    geometry = validate_polygon(PLOT)
    name = _overlay_filename(
        observed,
        plot_id=plot_id,
        scene_id="api-test-scene",
        geometry_digest=_geometry_digest(geometry),
    )
    path = root / f"{name}.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return path


def test_overlay_endpoint_returns_png_and_bounds(monkeypatch, request):
    path = _write_overlay()
    request.addfinalizer(lambda: path.unlink(missing_ok=True))
    monkeypatch.setattr(settings, "satellite_overlay_dir", "artifacts")

    response = get_satellite_overlay("MA-001", Database(_plot(), _recommendation()), SimpleNamespace(id=11, role="farmer"))

    assert response.media_type == "image/png"
    assert Path(response.path).resolve() == path.resolve()
    assert json.loads(response.headers["X-Qatra-Overlay-Bounds"]) == [-7.5898, 33.5731, -7.5888, 33.574]
    assert response.headers["X-Qatra-Overlay-Observed-At"] == "2026-11-01"


def test_overlay_endpoint_allows_assigned_advisor(monkeypatch, request):
    path = _write_overlay()
    request.addfinalizer(lambda: path.unlink(missing_ok=True))
    monkeypatch.setattr(settings, "satellite_overlay_dir", "artifacts")

    response = get_satellite_overlay("MA-001", Database(_plot(), _recommendation()), SimpleNamespace(id=22, role="advisor"))

    assert response.media_type == "image/png"


def test_overlay_endpoint_rejects_missing_or_unassigned_plot():
    with pytest.raises(HTTPException) as missing:
        get_satellite_overlay("MA-001", Database(None, None), SimpleNamespace(id=11, role="farmer"))
    assert missing.value.status_code == 404

    with pytest.raises(HTTPException) as denied:
        get_satellite_overlay("PRIVATE", DeniedDatabase(None, None), SimpleNamespace(id=11, role="farmer"))
    assert denied.value.status_code == 404


def test_overlay_endpoint_handles_missing_file(monkeypatch):
    monkeypatch.setattr(settings, "satellite_overlay_dir", "artifacts")
    with pytest.raises(HTTPException) as missing:
        get_satellite_overlay("MISSING", Database(_plot("MISSING"), _recommendation()), SimpleNamespace(id=11, role="farmer"))
    assert missing.value.status_code == 404


def test_overlay_path_cannot_escape_configured_directory():
    geometry = validate_polygon(PLOT)
    assert find_overlay_path_for_test("../../outside", geometry, "artifacts") is None


def find_overlay_path_for_test(plot_id, geometry, directory):
    from app.services.satellite_service import find_overlay_path

    return find_overlay_path(plot_id=plot_id, geometry=geometry, observed="2026-11-01", directory=directory)
