"""Reusable satellite observation service.

The live adapter uses Google Earth Engine (GEE) without triggering an
interactive login.  Shared-contract fields are exposed by
``to_contract_dict``; rendering and quality details remain internal here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)

OPTICAL_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
RADAR_COLLECTION = "COPERNICUS/S1_GRD"
MIN_VALID_PIXEL_PCT = 70.0
DEFAULT_LOOKBACK_DAYS = 10
SCL_INVALID_CLASSES = frozenset({0, 1, 2, 3, 8, 9, 10, 11})


class SatelliteServiceError(RuntimeError):
    """Controlled error raised by the satellite adapter."""


class EarthEngineUnavailable(SatelliteServiceError):
    """GEE is not installed, configured, authenticated, or reachable."""


class InvalidGeoJSON(SatelliteServiceError):
    """The supplied value is not a valid polygon GeoJSON object."""


@dataclass
class SatelliteObservation:
    ndvi: float | None
    ndwi: float | None
    ndvi_observed_at: str | None
    valid_pixel_pct: float | None
    satellite_source: str | None
    quality: str
    reason: str | None = None
    radar_fallback: bool = False
    vigor_map_path: str | None = None
    bounds: tuple[float, float, float, float] | None = None
    quality_details: dict[str, Any] = field(default_factory=dict)

    def to_contract_dict(self) -> dict[str, Any]:
        """Return only fields currently approved in ``docs/contract.json``."""
        return {
            "ndvi": self.ndvi,
            "ndwi": self.ndwi,
            "ndvi_observed_at": self.ndvi_observed_at,
            "valid_pixel_pct": self.valid_pixel_pct,
            "satellite_source": self.satellite_source,
        }


class SceneClient(Protocol):
    def observe(self, geometry: BaseGeometry, start: date, end: date) -> SatelliteObservation:
        ...


def validate_polygon(geojson: Mapping[str, Any] | BaseGeometry) -> BaseGeometry:
    """Validate a GeoJSON Polygon/MultiPolygon and return a Shapely geometry."""
    try:
        geometry = geojson if isinstance(geojson, BaseGeometry) else shape(geojson.get("geometry", geojson))
    except (AttributeError, TypeError, ValueError) as exc:
        raise InvalidGeoJSON("invalid_geojson") from exc
    if geometry.geom_type not in {"Polygon", "MultiPolygon"} or geometry.is_empty or not geometry.is_valid:
        raise InvalidGeoJSON("geojson_must_be_a_valid_polygon")
    minx, miny, maxx, maxy = geometry.bounds
    if not (-180 <= minx <= 180 and -180 <= maxx <= 180 and -90 <= miny <= 90 and -90 <= maxy <= 90):
        raise InvalidGeoJSON("polygon_coordinates_out_of_range")
    return geometry


def compute_indices(red: float, nir: float, swir: float) -> tuple[float | None, float | None]:
    """Compute NDVI and Gao NDWI from scaled or unscaled SR values."""
    values = (red / 10000.0, nir / 10000.0, swir / 10000.0) if max(abs(red), abs(nir), abs(swir)) > 2 else (red, nir, swir)
    red_r, nir_r, swir_r = values
    return _normalized_difference(nir_r, red_r), _normalized_difference(nir_r, swir_r)


def valid_pixel_percentage(valid_pixels: int, total_pixels: int) -> float | None:
    if total_pixels <= 0 or valid_pixels < 0 or valid_pixels > total_pixels:
        return None
    return round(valid_pixels * 100.0 / total_pixels, 2)


def is_valid_scl(class_value: int) -> bool:
    """Return whether an SCL class is usable for the optical indices."""
    return class_value not in SCL_INVALID_CLASSES


async def fetch_indices(
    bbox: list[float] | None = None,
    *,
    geojson: Mapping[str, Any] | BaseGeometry | None = None,
    analysis_date: date | str | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    offline_dir: str | Path | None = None,
    client: SceneClient | None = None,
    radar_client: SceneClient | None = None,
    generate_overlay: bool = True,
) -> SatelliteObservation:
    """Fetch the best optical observation, with radar/offline fallbacks."""
    try:
        geometry = _geometry_from_inputs(geojson, bbox)
    except InvalidGeoJSON as exc:
        return missing_optical(str(exc))

    end = _as_date(end_date or analysis_date or date.today())
    start = _as_date(start_date) if start_date else end - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    if start > end:
        return missing_optical("invalid_date_window")

    if offline_dir:
        offline = _read_offline_scene(Path(offline_dir), geometry)
        if offline is not None:
            return offline

    if client is not None:
        try:
            optical = await asyncio.to_thread(client.observe, geometry, start, end)
        except Exception as exc:
            logger.warning("satellite client failed: %s", type(exc).__name__)
            optical = missing_optical("satellite_api_unavailable")
    else:
        try:
            optical = await asyncio.to_thread(_observe_earth_engine, geometry, start, end, generate_overlay)
        except SatelliteServiceError as exc:
            logger.warning("Earth Engine unavailable: %s", exc)
            optical = missing_optical(str(exc))
        except Exception as exc:
            logger.warning("Earth Engine request failed: %s", type(exc).__name__)
            optical = missing_optical("satellite_api_unavailable")

    if optical.valid_pixel_pct is not None and optical.valid_pixel_pct >= MIN_VALID_PIXEL_PCT:
        return optical

    if radar_client is not None:
        try:
            radar = await asyncio.to_thread(radar_client.observe, geometry, start, end)
        except Exception as exc:
            logger.warning("injected Sentinel-1 client failed: %s", type(exc).__name__)
            radar = None
    elif client is not None:
        # An injected optical client is a complete offline seam. Do not
        # silently escape to a live Earth Engine call during unit tests.
        radar = None
    else:
        radar = _observe_sentinel1(geometry, start, end)
    if radar is not None:
        radar.reason = "optical_cloudy_or_unavailable"
        radar.radar_fallback = True
        radar.quality = "radar_fallback"
        if radar.valid_pixel_pct is None:
            radar.valid_pixel_pct = optical.valid_pixel_pct
        radar.quality_details = {
            **optical.quality_details,
            **radar.quality_details,
            "optical_valid_pixel_pct": optical.valid_pixel_pct,
        }
        return radar
    if optical.valid_pixel_pct is not None and optical.valid_pixel_pct < MIN_VALID_PIXEL_PCT:
        return SatelliteObservation(
            ndvi=None,
            ndwi=None,
            ndvi_observed_at=optical.ndvi_observed_at,
            valid_pixel_pct=optical.valid_pixel_pct,
            satellite_source=optical.satellite_source,
            quality="low_valid_pixels",
            reason="no_sentinel1_scene",
            bounds=optical.bounds,
            quality_details={
                **optical.quality_details,
                "optical_valid_pixel_pct": optical.valid_pixel_pct,
            },
        )
    optical.reason = optical.reason or "no_usable_optical_or_radar_scene"
    return optical


def sample_optical() -> SatelliteObservation:
    """Explicit test/demo fixture; never used as a live fallback."""
    return SatelliteObservation(0.68, 0.21, "2026-10-11", 86.0, "sentinel-2", "sample")


def missing_optical(reason: str = "no_scene") -> SatelliteObservation:
    return SatelliteObservation(None, None, None, None, None, "missing", reason=reason)


def maybe_sentinel1_fallback(optical: SatelliteObservation, radar: SatelliteObservation | None = None) -> SatelliteObservation:
    """Compatibility helper: never labels an absent radar scene as success."""
    if optical.satellite_source == "sentinel-1" or (optical.valid_pixel_pct is not None and optical.valid_pixel_pct >= MIN_VALID_PIXEL_PCT):
        return optical
    if radar is not None and radar.satellite_source == "sentinel-1" and radar.ndvi is None:
        radar.radar_fallback = True
        radar.quality = "radar_fallback"
        return radar
    return optical


def _observe_earth_engine(geometry: BaseGeometry, start: date, end: date, generate_overlay: bool) -> SatelliteObservation:
    try:
        import ee  # type: ignore
    except ImportError as exc:
        raise EarthEngineUnavailable("earthengine_not_installed") from exc
    from app.core.config import settings

    if not settings.gee_project_id:
        raise EarthEngineUnavailable("gee_project_id_missing")
    try:
        _initialize_ee(ee, settings.gee_project_id, settings.gee_credentials_path)
        region = ee.Geometry(geometry.__geo_interface__)
        collection = (
            ee.ImageCollection(OPTICAL_COLLECTION).filterBounds(region)
            .filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat())
            .sort("CLOUDY_PIXEL_PERCENTAGE")
        )
        if not collection.size().getInfo():
            return missing_optical("no_sentinel2_scene")

        def mask_scl(image: Any) -> Any:
            scl = image.select("SCL")
            # 0 no data; 1 saturated/defective; 2 dark/shadow; 3 shadow;
            # 8/9/10 cloud/cirrus; 11 snow/ice.
            mask = scl.neq(0).And(scl.neq(1)).And(scl.neq(2)).And(scl.neq(3)).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
            return image.updateMask(mask)

        image = ee.Image(collection.map(mask_scl).first())
        # Harmonized L2A SR is scaled by 10,000; convert before calculating ratios.
        reflectance = image.select(["B4", "B8", "B11"]).divide(10000)
        ndvi = reflectance.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndwi = reflectance.normalizedDifference(["B8", "B11"]).rename("NDWI_GAO")
        valid = ndvi.mask().reduce(ee.Reducer.min()).rename("valid")
        stats = valid.reduceRegion(ee.Reducer.mean(), region, 10, maxPixels=1_000_000, bestEffort=True).getInfo()
        valid_pct = round(float(stats.get("valid", 0.0)) * 100.0, 2) if stats.get("valid") is not None else None
        props = image.getInfo().get("properties", {})
        observed = _timestamp_to_date(props.get("system:time_start"))
        observation = SatelliteObservation(
            ndvi=_region_mean(ndvi, region, ee), ndwi=_region_mean(ndwi, region, ee),
            ndvi_observed_at=observed, valid_pixel_pct=valid_pct,
            satellite_source="sentinel-2", quality="good" if valid_pct is not None and valid_pct >= MIN_VALID_PIXEL_PCT else "low_valid_pixels",
            bounds=tuple(float(v) for v in geometry.bounds),
            quality_details={"collection": OPTICAL_COLLECTION, "cloud_mask": "SCL", "ndwi_formula": "gao"},
        )
        if generate_overlay and observed:
            observation.vigor_map_path = _render_overlay(ndvi, region, observed, ee)
        return observation
    except EarthEngineUnavailable:
        raise
    except Exception as exc:
        raise SatelliteServiceError("earth_engine_request_failed") from exc


def _observe_sentinel1(geometry: BaseGeometry, start: date, end: date) -> SatelliteObservation | None:
    try:
        import ee  # type: ignore
        from app.core.config import settings
        if not settings.gee_project_id:
            return None
        _initialize_ee(ee, settings.gee_project_id, settings.gee_credentials_path)
        region = ee.Geometry(geometry.__geo_interface__)
        collection = ee.ImageCollection(RADAR_COLLECTION).filterBounds(region).filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat()).sort("system:time_start", False)
        if not collection.size().getInfo():
            return None
        image = ee.Image(collection.first()).getInfo()
        return SatelliteObservation(None, None, _timestamp_to_date(image.get("properties", {}).get("system:time_start")), None, "sentinel-1", "radar_fallback", bounds=tuple(float(v) for v in geometry.bounds), quality_details={"collection": RADAR_COLLECTION})
    except Exception as exc:
        logger.warning("Sentinel-1 fallback unavailable: %s", type(exc).__name__)
        return None


def _read_offline_scene(directory: Path, geometry: BaseGeometry) -> SatelliteObservation | None:
    if not directory.is_dir():
        return None
    for manifest in sorted(directory.glob("*.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if data.get("type") not in {"qatra-satellite-scene", "sentinel-2-scene"}:
                continue
            scene_bounds = data.get("bounds")
            if scene_bounds:
                scene = shape({
                    "type": "Polygon",
                    "coordinates": [[
                        [scene_bounds[0], scene_bounds[1]],
                        [scene_bounds[2], scene_bounds[1]],
                        [scene_bounds[2], scene_bounds[3]],
                        [scene_bounds[0], scene_bounds[3]],
                        [scene_bounds[0], scene_bounds[1]],
                    ]],
                })
                if not geometry.intersects(scene):
                    continue
            if not data.get("observed_at") or data.get("ndvi") is None or data.get("valid_pixel_pct") is None:
                continue
            return SatelliteObservation(float(data["ndvi"]), _optional_float(data.get("ndwi")), str(data["observed_at"])[:10], float(data["valid_pixel_pct"]), "sentinel-2", "offline", vigor_map_path=data.get("vigor_map_path"), bounds=tuple(scene_bounds) if scene_bounds else tuple(float(v) for v in geometry.bounds), quality_details={"manifest": str(manifest)})
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            logger.warning("Ignoring invalid offline satellite manifest: %s", manifest.name)
    return None


def _initialize_ee(ee: Any, project: str, credentials_path: str) -> None:
    if credentials_path:
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", credentials_path)
    try:
        ee.Initialize(project=project)
    except Exception as exc:
        raise EarthEngineUnavailable("earth_engine_authentication_failed") from exc


def _render_overlay(ndvi: Any, region: Any, observed: str, ee: Any) -> str | None:
    from app.core.config import settings
    output_dir = Path(settings.satellite_overlay_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"ndvi_{observed}.png"
    try:
        url = ndvi.visualize(min=-1, max=1, palette=["#440154", "#21918c", "#fde725"], forceRgbOutput=True).getThumbURL({"region": region, "dimensions": 1024, "format": "png"})
        urllib.request.urlretrieve(url, output)
        return str(output)
    except Exception as exc:
        logger.warning("NDVI overlay generation failed: %s", type(exc).__name__)
        return None


def _region_mean(image: Any, region: Any, ee: Any) -> float | None:
    value = image.reduceRegion(ee.Reducer.mean(), region, 10, maxPixels=1_000_000, bestEffort=True).getInfo()
    raw = value.get(image.bandNames().get(0).getInfo())
    return round(float(raw), 6) if raw is not None else None


def _geometry_from_inputs(geojson: Mapping[str, Any] | BaseGeometry | None, bbox: list[float] | None) -> BaseGeometry:
    if geojson is not None:
        return validate_polygon(geojson)
    if bbox is None or len(bbox) != 4:
        raise InvalidGeoJSON("parcel_polygon_required")
    minx, miny, maxx, maxy = map(float, bbox)
    return validate_polygon({"type": "Polygon", "coordinates": [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]]})


def _as_date(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _timestamp_to_date(value: Any) -> str | None:
    return None if value is None else datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).date().isoformat()


def _normalized_difference(first: float, second: float) -> float | None:
    denominator = first + second
    return round((first - second) / denominator, 6) if denominator else None


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
