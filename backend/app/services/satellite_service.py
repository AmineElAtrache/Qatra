"""Satellite seat — Copernicus Data Space. Missing image stays null."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class SatelliteObservation:
    ndvi: float | None
    ndwi: float | None
    ndvi_observed_at: str | None
    valid_pixel_pct: float | None
    satellite_source: str | None
    quality: str
    reason: str | None = None


async def fetch_indices(bbox: list[float] | None = None) -> SatelliteObservation:
    """
    TODO (Satellite seat): call Copernicus Data Space.
    Until credentials exist, return the contract sample for MA-001
    or an honest missing observation.
    """
    _ = bbox
    if not _has_credentials():
        return sample_optical()
    # Placeholder for live path — keep nulls honest if fetch fails.
    return SatelliteObservation(
        ndvi=None,
        ndwi=None,
        ndvi_observed_at=None,
        valid_pixel_pct=None,
        satellite_source=None,
        quality="missing",
        reason="copernicus_not_wired",
    )


def sample_optical() -> SatelliteObservation:
    return SatelliteObservation(
        ndvi=0.68,
        ndwi=0.21,
        ndvi_observed_at="2026-10-11",
        valid_pixel_pct=86.0,
        satellite_source="sentinel-2",
        quality="sample",
    )


def missing_optical(reason: str = "no_scene") -> SatelliteObservation:
    return SatelliteObservation(
        ndvi=None,
        ndwi=None,
        ndvi_observed_at=None,
        valid_pixel_pct=None,
        satellite_source=None,
        quality="missing",
        reason=reason,
    )


def maybe_sentinel1_fallback(optical: SatelliteObservation) -> SatelliteObservation:
    """Radar is a confidence flag — never invent NDVI."""
    if optical.valid_pixel_pct is not None and optical.valid_pixel_pct >= 70:
        return optical
    return SatelliteObservation(
        ndvi=None,
        ndwi=None,
        ndvi_observed_at=optical.ndvi_observed_at or date.today().isoformat(),
        valid_pixel_pct=optical.valid_pixel_pct,
        satellite_source="sentinel-1",
        quality="radar_fallback",
        reason="optical_cloudy_or_old",
    )


def _has_credentials() -> bool:
    from app.core.config import settings

    return bool(settings.copernicus_client_id and settings.copernicus_client_secret)
