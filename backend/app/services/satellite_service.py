"""Reusable satellite observation service.

The live adapter uses Google Earth Engine (GEE) without triggering an
interactive login.  Shared-contract fields are exposed by
``to_contract_dict``; rendering and quality details remain internal here.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)

OPTICAL_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
RADAR_COLLECTION = "COPERNICUS/S1_GRD"
MIN_VALID_PIXEL_PCT = 70.0
DEFAULT_LOOKBACK_DAYS = 10
MAX_OBSERVATION_AGE_DAYS = 10
REQUIRED_OPTICAL_BANDS = ("B4", "B8", "B11")
SCL_INVALID_CLASSES = frozenset({0, 1, 2, 3, 8, 9, 10, 11})
OVERLAY_PALETTES = {
    "ndvi": ("#440154", "#21918c", "#fde725"),
    "ndmi": ("#8c510a", "#f6e8c3", "#5ab4ac", "#01665e"),
}
OVERLAY_FORMULAS = {
    "ndvi": "(B08-B04)/(B08+B04)",
    "ndmi": "gao_ndwi_ndmi:(B08-B11)/(B08+B11)",
}


class SatelliteServiceError(RuntimeError):
    """Controlled error raised by the satellite adapter."""


class EarthEngineUnavailable(SatelliteServiceError):
    """GEE is not installed, configured, authenticated, or reachable."""


class InvalidGeoJSON(SatelliteServiceError):
    """The supplied value is not a valid polygon GeoJSON object."""


class IncompatibleSatelliteObservations(SatelliteServiceError):
    """Raised when two observations cannot be compared safely."""


@dataclass
class SatelliteAcquisition:
    """One optical Sentinel-2 acquisition for temporal analysis."""

    scene_id: str | None
    observed_at: str | None
    ndvi: float | None
    ndmi: float | None
    valid_pixel_pct: float | None
    quality: str
    satellite_source: str = "sentinel-2"
    bounds: tuple[float, float, float, float] | None = None
    quality_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SatelliteComparison:
    """Difference between two compatible optical acquisitions."""

    earlier_scene_id: str | None
    later_scene_id: str | None
    earlier_observed_at: str
    later_observed_at: str
    ndvi_change: float
    ndmi_change: float
    valid_pixel_pct: float
    quality: str
    bounds: tuple[float, float, float, float] | None = None


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
    ndmi_map_path: str | None = None
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


class TimeSeriesSceneClient(Protocol):
    def observe_many(self, geometry: BaseGeometry, start: date, end: date) -> Sequence[SatelliteAcquisition]:
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


def compute_indices(
    red: float | None,
    nir: float | None,
    swir: float | None,
) -> tuple[float | None, float | None]:
    """Compute NDVI and Gao NDWI/NDMI from scaled or unscaled SR values.

    The second returned value remains the contract's ``ndwi`` field for
    compatibility, but its formula is Gao NDWI (also commonly called NDMI):
    ``(B08-B11)/(B08+B11)``. McFeeters NDWI is a different B03/B08 index.
    """
    if red is None or nir is None or swir is None:
        return None, None
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


def missing_required_bands(
    available_bands: Sequence[str],
    required_bands: Sequence[str] = (*REQUIRED_OPTICAL_BANDS, "SCL"),
) -> tuple[str, ...]:
    """Return required Sentinel-2 bands absent from a scene."""
    available = set(available_bands)
    return tuple(band for band in required_bands if band not in available)


def combined_valid_pixel_mask(
    scl_values: Sequence[int | None],
    band_valid_masks: Mapping[str, Sequence[bool]],
) -> list[bool]:
    """Combine SCL validity with masks for every required index band.

    This pure helper mirrors the Earth Engine mask operation and makes the
    pixel-quality rule deterministic to test without a live provider.
    """
    missing = missing_required_bands(tuple(band_valid_masks), REQUIRED_OPTICAL_BANDS)
    if missing:
        raise SatelliteServiceError(f"missing_required_bands:{','.join(missing)}")
    lengths = {len(scl_values), *(len(band_valid_masks[band]) for band in REQUIRED_OPTICAL_BANDS)}
    if len(lengths) != 1:
        raise SatelliteServiceError("inconsistent_pixel_mask_lengths")
    return [
        scl is not None
        and is_valid_scl(int(scl))
        and all(band_valid_masks[band][index] for band in REQUIRED_OPTICAL_BANDS)
        for index, scl in enumerate(scl_values)
    ]


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
    plot_id: str | None = None,
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
        offline = _read_offline_scene(Path(offline_dir), geometry, reference_date=end)
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
            optical = await asyncio.to_thread(
                _observe_earth_engine,
                geometry,
                start,
                end,
                generate_overlay,
                plot_id or _plot_identifier(geojson),
            )
        except SatelliteServiceError as exc:
            logger.warning("Earth Engine unavailable: %s", exc)
            optical = missing_optical(str(exc))
        except Exception as exc:
            logger.warning("Earth Engine request failed: %s", type(exc).__name__)
            optical = missing_optical("satellite_api_unavailable")

    optical = _validate_optical_freshness(optical, reference_date=end)

    if _optical_is_usable(optical):
        return optical

    optical_rejection_reason = _optical_rejection_reason(optical)

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
        radar.reason = optical_rejection_reason
        radar.radar_fallback = True
        radar.quality = "radar_fallback"
        radar.quality_details = {
            **optical.quality_details,
            **radar.quality_details,
            "optical_rejection_reason": optical_rejection_reason,
            "optical_valid_pixel_pct": optical.valid_pixel_pct,
            "optical_quality": optical.quality,
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
    if optical.reason is None:
        optical.reason = "no_sentinel1_scene" if optical_rejection_reason != "no_sentinel2_scene" else optical_rejection_reason
    if not optical.quality:
        optical.quality = "incomplete_optical"
    return optical


async def fetch_acquisitions(
    *,
    geojson: Mapping[str, Any] | BaseGeometry,
    start_date: date | str,
    end_date: date | str,
    client: TimeSeriesSceneClient | None = None,
    max_acquisitions: int | None = None,
) -> list[SatelliteAcquisition]:
    """Retrieve sorted, de-duplicated Sentinel-2 acquisitions for a parcel.

    This is an optical-only time-series path. It deliberately does not invoke
    Sentinel-1 fallback because radar cannot provide NDVI or NDMI. Provider
    scenes are reused from one collection query, and comparison is performed
    later on the returned observations without another Earth Engine request.
    """
    geometry = validate_polygon(geojson)
    start = _as_date(start_date)
    end = _as_date(end_date)
    if start > end:
        raise SatelliteServiceError("invalid_date_window")
    if max_acquisitions is not None and max_acquisitions <= 0:
        raise SatelliteServiceError("invalid_max_acquisitions")

    if client is not None:
        acquisitions = await asyncio.to_thread(client.observe_many, geometry, start, end)
    else:
        acquisitions = await asyncio.to_thread(_observe_earth_engine_series, geometry, start, end)

    normalized = _normalize_acquisitions(acquisitions, geometry, start, end)
    return normalized[:max_acquisitions] if max_acquisitions is not None else normalized


def compare_acquisitions(
    earlier: SatelliteAcquisition,
    later: SatelliteAcquisition,
) -> SatelliteComparison:
    """Compare two compatible, high-quality optical acquisitions.

    No agronomic threshold is applied. Changes are raw index differences and
    must be interpreted by Backend/Agronomy with other observations.
    """
    if earlier.satellite_source != "sentinel-2" or later.satellite_source != "sentinel-2":
        raise IncompatibleSatelliteObservations("optical_sentinel2_only")
    if not earlier.observed_at or not later.observed_at:
        raise IncompatibleSatelliteObservations("missing_observation_date")
    if not earlier.scene_id or not later.scene_id:
        raise IncompatibleSatelliteObservations("missing_scene_id")
    if earlier.scene_id == later.scene_id:
        raise IncompatibleSatelliteObservations("same_scene")
    if earlier.observed_at >= later.observed_at:
        raise IncompatibleSatelliteObservations("dates_not_chronological")
    if earlier.bounds != later.bounds:
        raise IncompatibleSatelliteObservations("geometry_mismatch")
    for observation in (earlier, later):
        if observation.quality != "good":
            raise IncompatibleSatelliteObservations("observation_quality_not_good")
        if observation.valid_pixel_pct is None or observation.valid_pixel_pct < MIN_VALID_PIXEL_PCT:
            raise IncompatibleSatelliteObservations("observation_coverage_below_threshold")
        if observation.ndvi is None or observation.ndmi is None:
            raise IncompatibleSatelliteObservations("observation_indices_missing")

    return SatelliteComparison(
        earlier_scene_id=earlier.scene_id,
        later_scene_id=later.scene_id,
        earlier_observed_at=earlier.observed_at,
        later_observed_at=later.observed_at,
        ndvi_change=round(later.ndvi - earlier.ndvi, 6),
        ndmi_change=round(later.ndmi - earlier.ndmi, 6),
        valid_pixel_pct=min(earlier.valid_pixel_pct, later.valid_pixel_pct),
        quality="compatible",
        bounds=earlier.bounds,
    )


def _normalize_acquisitions(
    acquisitions: Sequence[SatelliteAcquisition],
    geometry: BaseGeometry,
    start: date,
    end: date,
) -> list[SatelliteAcquisition]:
    normalized: list[SatelliteAcquisition] = []
    seen: set[tuple[str | None, str]] = set()
    bounds = tuple(float(value) for value in geometry.bounds)
    for acquisition in acquisitions:
        if acquisition.satellite_source != "sentinel-2" or not acquisition.observed_at:
            continue
        try:
            observed = date.fromisoformat(acquisition.observed_at[:10])
        except (TypeError, ValueError):
            continue
        if observed < start or observed > end:
            continue
        key = (acquisition.scene_id, acquisition.observed_at[:10])
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            SatelliteAcquisition(
                scene_id=acquisition.scene_id,
                observed_at=acquisition.observed_at,
                ndvi=acquisition.ndvi,
                ndmi=acquisition.ndmi,
                valid_pixel_pct=acquisition.valid_pixel_pct,
                quality=acquisition.quality,
                satellite_source="sentinel-2",
                bounds=acquisition.bounds or bounds,
                quality_details=dict(acquisition.quality_details),
            )
        )
    return sorted(normalized, key=lambda item: (item.observed_at or "", item.scene_id or ""))


def sample_optical() -> SatelliteObservation:
    """Explicit test/demo fixture; never used as a live fallback."""
    return SatelliteObservation(0.68, 0.21, "2026-10-11", 86.0, "sentinel-2", "sample")


def missing_optical(
    reason: str = "no_scene",
    *,
    quality_details: dict[str, Any] | None = None,
) -> SatelliteObservation:
    return SatelliteObservation(
        None,
        None,
        None,
        None,
        None,
        "missing",
        reason=reason,
        quality_details=quality_details or {},
    )


def _observation_freshness(observed_at: str, reference_date: date) -> str:
    """Classify an observation date relative to the requested analysis date."""
    try:
        observed = date.fromisoformat(str(observed_at)[:10])
    except (TypeError, ValueError):
        return "invalid"
    age_days = (reference_date - observed).days
    if age_days < 0:
        return "invalid"
    return "fresh" if age_days <= MAX_OBSERVATION_AGE_DAYS else "stale"


def _validate_optical_freshness(
    observation: SatelliteObservation,
    *,
    reference_date: date,
) -> SatelliteObservation:
    """Reject stale/invalid optical observations without returning their values."""
    if observation.satellite_source not in {"sentinel-2", "offline"}:
        return observation
    if observation.ndvi_observed_at is None:
        return observation
    freshness = _observation_freshness(observation.ndvi_observed_at, reference_date)
    if freshness == "fresh":
        observation.quality_details = {**observation.quality_details, "freshness": freshness}
        return observation
    reason = "stale_observation" if freshness == "stale" else "invalid_observation_date"
    return missing_optical(
        reason,
        quality_details={
            **observation.quality_details,
            "observed_at": observation.ndvi_observed_at,
            "reference_date": reference_date.isoformat(),
            "freshness": freshness,
        },
    )


def _optical_is_usable(observation: SatelliteObservation) -> bool:
    """Return whether optical data is complete enough to skip radar fallback."""
    if observation.satellite_source not in {"sentinel-2", "offline"}:
        return False
    if observation.valid_pixel_pct is None or observation.valid_pixel_pct < MIN_VALID_PIXEL_PCT:
        return False
    if observation.ndvi is None or observation.ndwi is None:
        return False
    return observation.quality not in {None, "", "missing", "low_valid_pixels", "incomplete_optical"}


def _optical_rejection_reason(observation: SatelliteObservation) -> str:
    if observation.reason:
        return observation.reason
    if observation.satellite_source not in {"sentinel-2", "offline"} or observation.ndvi_observed_at is None:
        return "no_sentinel2_scene"
    if observation.valid_pixel_pct is None:
        return "optical_valid_pixel_pct_missing"
    if observation.valid_pixel_pct < MIN_VALID_PIXEL_PCT:
        return "optical_low_valid_pixels"
    if observation.ndvi is None or observation.ndwi is None:
        return "optical_indices_incomplete"
    if not observation.quality or observation.quality == "missing":
        return "optical_quality_missing"
    return "optical_unusable"


def maybe_sentinel1_fallback(optical: SatelliteObservation, radar: SatelliteObservation | None = None) -> SatelliteObservation:
    """Compatibility helper: never labels an absent radar scene as success."""
    if optical.satellite_source == "sentinel-1" or _optical_is_usable(optical):
        return optical
    if radar is not None and radar.satellite_source == "sentinel-1" and radar.ndvi is None:
        radar.radar_fallback = True
        radar.quality = "radar_fallback"
        radar.reason = _optical_rejection_reason(optical)
        radar.quality_details = {
            **optical.quality_details,
            **radar.quality_details,
            "optical_rejection_reason": radar.reason,
            "optical_valid_pixel_pct": optical.valid_pixel_pct,
            "optical_quality": optical.quality,
        }
        return radar
    return optical


def _observe_earth_engine(
    geometry: BaseGeometry,
    start: date,
    end: date,
    generate_overlay: bool,
    plot_id: str | None = None,
) -> SatelliteObservation:
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
        available_bands = tuple(str(value) for value in image.bandNames().getInfo())
        missing_bands = missing_required_bands(available_bands)
        if missing_bands:
            return SatelliteObservation(
                None,
                None,
                None,
                None,
                "sentinel-2",
                "missing_bands",
                reason="missing_required_bands",
                quality_details={
                    "collection": OPTICAL_COLLECTION,
                    "available_bands": available_bands,
                    "missing_bands": missing_bands,
                },
            )
        # Harmonized L2A SR is scaled by 10,000; convert before calculating ratios.
        reflectance = image.select(list(REQUIRED_OPTICAL_BANDS)).divide(10000)
        ndvi = reflectance.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndwi = reflectance.normalizedDifference(["B8", "B11"]).rename("NDWI_GAO")
        # The SCL mask is already applied to the image. Reducing the masks of
        # all required bands prevents a missing SWIR pixel from being counted
        # as valid merely because B04/B08 were usable.
        valid = image.select(list(REQUIRED_OPTICAL_BANDS)).mask().reduce(ee.Reducer.min()).rename("valid")
        stats = valid.reduceRegion(ee.Reducer.mean(), region, 10, maxPixels=1_000_000, bestEffort=True).getInfo()
        valid_pct = round(float(stats.get("valid", 0.0)) * 100.0, 2) if stats.get("valid") is not None else None
        props = image.getInfo().get("properties", {})
        observed = _timestamp_to_date(props.get("system:time_start"))
        scene_id = _scene_identifier(props)
        observation = SatelliteObservation(
            ndvi=_region_mean(ndvi, region, ee), ndwi=_region_mean(ndwi, region, ee),
            ndvi_observed_at=observed, valid_pixel_pct=valid_pct,
            satellite_source="sentinel-2", quality="good" if valid_pct is not None and valid_pct >= MIN_VALID_PIXEL_PCT else "low_valid_pixels",
            bounds=tuple(float(v) for v in geometry.bounds),
            quality_details={
                "collection": OPTICAL_COLLECTION,
                "cloud_mask": "SCL",
                "required_bands": REQUIRED_OPTICAL_BANDS,
                "ndvi_formula": OVERLAY_FORMULAS["ndvi"],
                "ndwi_formula": OVERLAY_FORMULAS["ndmi"],
            },
        )
        observation.quality_details["overlay_metadata"] = {
            index_type: _overlay_metadata(index_type, observed, observation.bounds, None)
            for index_type in ("ndvi", "ndmi")
        }
        if generate_overlay and observed:
            geometry_digest = _geometry_digest(geometry)
            observation.vigor_map_path = _render_overlay(
                ndvi,
                region,
                observed,
                ee,
                index_type="ndvi",
                plot_id=plot_id,
                scene_id=scene_id,
                geometry_digest=geometry_digest,
            )
            observation.ndmi_map_path = _render_overlay(
                ndwi,
                region,
                observed,
                ee,
                index_type="ndmi",
                plot_id=plot_id,
                scene_id=scene_id,
                geometry_digest=geometry_digest,
            )
            observation.quality_details["overlay_metadata"] = {
                index_type: _overlay_metadata(
                    index_type,
                    observed,
                    observation.bounds,
                    path,
                )
                for index_type, path in (
                    ("ndvi", observation.vigor_map_path),
                    ("ndmi", observation.ndmi_map_path),
                )
            }
        return observation
    except EarthEngineUnavailable:
        raise
    except Exception as exc:
        raise SatelliteServiceError("earth_engine_request_failed") from exc


def _observe_earth_engine_series(
    geometry: BaseGeometry,
    start: date,
    end: date,
) -> list[SatelliteAcquisition]:
    """Read a Sentinel-2 collection once and reduce each acquisition."""
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
            ee.ImageCollection(OPTICAL_COLLECTION)
            .filterBounds(region)
            .filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat())
            .sort("system:time_start")
        )
        count = int(collection.size().getInfo())
        if count == 0:
            return []
        images = collection.toList(count)
        return [
            _observe_earth_engine_acquisition(ee.Image(images.get(index)), geometry, region, ee)
            for index in range(count)
        ]
    except EarthEngineUnavailable:
        raise
    except Exception as exc:
        raise SatelliteServiceError("earth_engine_request_failed") from exc


def _observe_earth_engine_acquisition(
    image: Any,
    geometry: BaseGeometry,
    region: Any,
    ee: Any,
) -> SatelliteAcquisition:
    """Compute parcel statistics for one already-selected Sentinel-2 image."""
    scl = image.select("SCL")
    mask = (
        scl.neq(0)
        .And(scl.neq(1))
        .And(scl.neq(2))
        .And(scl.neq(3))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )
    masked = image.updateMask(mask)
    available_bands = tuple(str(value) for value in image.bandNames().getInfo())
    missing_bands = missing_required_bands(available_bands)
    properties = image.getInfo().get("properties", {})
    observed = _timestamp_to_date(properties.get("system:time_start"))
    scene_id = _scene_identifier(properties)
    bounds = tuple(float(value) for value in geometry.bounds)
    details: dict[str, Any] = {
        "collection": OPTICAL_COLLECTION,
        "cloud_mask": "SCL",
        "required_bands": REQUIRED_OPTICAL_BANDS,
        "ndvi_formula": OVERLAY_FORMULAS["ndvi"],
        "ndmi_formula": OVERLAY_FORMULAS["ndmi"],
    }
    if missing_bands:
        return SatelliteAcquisition(
            scene_id=scene_id,
            observed_at=observed,
            ndvi=None,
            ndmi=None,
            valid_pixel_pct=None,
            quality="missing_bands",
            bounds=bounds,
            quality_details={**details, "available_bands": available_bands, "missing_bands": missing_bands},
        )

    reflectance = masked.select(list(REQUIRED_OPTICAL_BANDS)).divide(10000)
    ndvi = reflectance.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndmi = reflectance.normalizedDifference(["B8", "B11"]).rename("NDMI_GAO")
    valid = masked.select(list(REQUIRED_OPTICAL_BANDS)).mask().reduce(ee.Reducer.min()).rename("valid")
    stats = valid.reduceRegion(ee.Reducer.mean(), region, 10, maxPixels=1_000_000, bestEffort=True).getInfo()
    valid_pct = round(float(stats.get("valid", 0.0)) * 100.0, 2) if stats.get("valid") is not None else None
    ndvi_value = _region_mean(ndvi, region, ee)
    ndmi_value = _region_mean(ndmi, region, ee)
    quality = "good" if valid_pct is not None and valid_pct >= MIN_VALID_PIXEL_PCT else "low_valid_pixels"
    return SatelliteAcquisition(
        scene_id=scene_id,
        observed_at=observed,
        ndvi=ndvi_value,
        ndmi=ndmi_value,
        valid_pixel_pct=valid_pct,
        quality=quality,
        bounds=bounds,
        quality_details=details,
    )


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


def _read_offline_scene(
    directory: Path,
    geometry: BaseGeometry,
    *,
    reference_date: date,
) -> SatelliteObservation | None:
    if not directory.is_dir():
        return None
    stale_observations: list[str] = []
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
            observed_at = str(data["observed_at"])
            freshness = _observation_freshness(observed_at, reference_date)
            if freshness != "fresh":
                if freshness == "stale":
                    stale_observations.append(observed_at[:10])
                continue
            return SatelliteObservation(float(data["ndvi"]), _optional_float(data.get("ndwi")), observed_at[:10], float(data["valid_pixel_pct"]), "sentinel-2", "offline", vigor_map_path=data.get("vigor_map_path"), bounds=tuple(scene_bounds) if scene_bounds else tuple(float(v) for v in geometry.bounds), quality_details={"manifest": str(manifest), "freshness": "fresh"})
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            logger.warning("Ignoring invalid offline satellite manifest: %s", manifest.name)
    if stale_observations:
        return missing_optical(
            "stale_offline_scene",
            quality_details={"stale_observed_at": sorted(stale_observations)},
        )
    return None


def _initialize_ee(ee: Any, project: str, credentials_path: str) -> None:
    if credentials_path:
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", credentials_path)
    try:
        ee.Initialize(project=project)
    except Exception as exc:
        raise EarthEngineUnavailable("earth_engine_authentication_failed") from exc


def _render_overlay(
    index_image: Any,
    region: Any,
    observed: str,
    ee: Any,
    *,
    index_type: str = "ndvi",
    plot_id: str | None = None,
    scene_id: str | None = None,
    geometry_digest: str | None = None,
) -> str | None:
    from app.core.config import settings

    index_type, palette, _ = _overlay_spec(index_type)
    output_dir = Path(settings.satellite_overlay_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{_overlay_filename(observed, index_type=index_type, plot_id=plot_id, scene_id=scene_id, geometry_digest=geometry_digest)}.png"
    temporary_path: Path | None = None
    try:
        # clip() is important: region controls the thumbnail viewport, but does
        # not by itself mask pixels outside the parcel. Existing cloud/no-data
        # masks are preserved by clip() and therefore remain transparent in PNG.
        clipped_image = index_image.clip(region)
        url = clipped_image.visualize(
            min=-1,
            max=1,
            palette=list(palette),
            forceRgbOutput=True,
        ).getThumbURL({"region": region, "dimensions": 1024, "format": "png"})
        # A UUID staging name avoids collisions between workers. The final
        # replace is atomic on the same filesystem.
        temporary_path = output_dir / f".{output.name}.{uuid.uuid4().hex}.tmp"
        urllib.request.urlretrieve(url, str(temporary_path))
        os.replace(temporary_path, output)
        temporary_path = None
        return str(output)
    except Exception as exc:
        logger.warning("%s overlay generation failed: %s", index_type.upper(), type(exc).__name__)
        return None
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass


def _plot_identifier(geojson: Mapping[str, Any] | BaseGeometry | None) -> str | None:
    if not isinstance(geojson, Mapping):
        return None
    properties = geojson.get("properties")
    if isinstance(properties, Mapping):
        value = properties.get("plot_id") or properties.get("public_id") or properties.get("id")
        return str(value) if value is not None else None
    return None


def _scene_identifier(properties: Mapping[str, Any]) -> str | None:
    for key in ("PRODUCT_ID", "system:index", "system:id"):
        value = properties.get(key)
        if value:
            return str(value)
    return None


def _safe_filename_token(value: str | None, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", value or "").strip("-._")
    return token or fallback


def _overlay_filename(
    observed: str,
    *,
    index_type: str = "ndvi",
    plot_id: str | None = None,
    scene_id: str | None = None,
    geometry_digest: str | None = None,
) -> str:
    """Return a deterministic filename that is unique per plot/scene."""
    index_type, _, _ = _overlay_spec(index_type)
    geometry_token = _safe_filename_token(geometry_digest, "unknown-geometry")
    scene_digest = hashlib.sha256((scene_id or "unknown-scene").encode("utf-8")).hexdigest()[:12]
    plot_token = _safe_filename_token(plot_id, "plot")
    return f"{index_type}_{plot_token}_{geometry_token}_{_safe_filename_token(observed, 'unknown-date')}_{scene_digest}"


def _overlay_spec(index_type: str) -> tuple[str, tuple[str, ...], str]:
    """Return the canonical overlay key, palette, and formula."""
    aliases = {"ndvi": "ndvi", "ndmi": "ndmi", "ndwi": "ndmi", "gao_ndwi": "ndmi"}
    canonical = aliases.get(index_type.lower())
    if canonical is None:
        raise SatelliteServiceError(f"unsupported_overlay_index:{index_type}")
    return canonical, OVERLAY_PALETTES[canonical], OVERLAY_FORMULAS[canonical]


def _overlay_metadata(
    index_type: str,
    observed: str,
    bounds: tuple[float, float, float, float] | None,
    path: str | None,
) -> dict[str, Any]:
    canonical, palette, formula = _overlay_spec(index_type)
    return {
        "index_type": canonical,
        "formula": formula,
        "observed_at": observed,
        "bounds": list(bounds) if bounds is not None else None,
        "palette": list(palette),
        "path": path,
    }


def _geometry_digest(geometry: BaseGeometry) -> str:
    payload = json.dumps(geometry.__geo_interface__, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def find_overlay_path(
    *,
    plot_id: str,
    geometry: BaseGeometry,
    observed: str,
    directory: str | Path,
    index_type: str = "ndvi",
) -> Path | None:
    """Resolve an overlay only from trusted plot metadata and a fixed directory."""
    index_type, _, _ = _overlay_spec(index_type)
    root = Path(directory).resolve()
    if not root.is_dir():
        return None
    prefix = (
        f"{index_type}_{_safe_filename_token(plot_id, 'plot')}_"
        f"{_geometry_digest(geometry)}_{_safe_filename_token(observed, 'unknown-date')}_"
    )
    for candidate in sorted(root.glob(f"{prefix}*.png"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            if candidate.is_file() and candidate.resolve().parent == root:
                return candidate
        except OSError:
            continue
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
