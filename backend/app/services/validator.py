"""Backend seat — decide show_dose vs needs_check. Never invent numbers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


MAX_WEATHER_AGE_HOURS = 48
MAX_SAT_AGE_DAYS = 10
MIN_VALID_PIXELS = 70.0


@dataclass
class ValidationInput:
    stage: str | None
    irrigation_method: str | None
    weather_observed_at: str | None
    ndvi: float | None
    ndvi_observed_at: str | None
    valid_pixel_pct: float | None


@dataclass
class ValidationResult:
    status: str  # show_dose | needs_check
    reasons: list[str]


def validate(inp: ValidationInput) -> ValidationResult:
    reasons: list[str] = []

    if not inp.stage:
        reasons.append("missing_stage")
    if not inp.irrigation_method:
        reasons.append("missing_irrigation_method")

    if not inp.weather_observed_at:
        reasons.append("missing_weather")
    else:
        age_h = _hours_since(inp.weather_observed_at)
        if age_h is not None and age_h > MAX_WEATHER_AGE_HOURS:
            reasons.append("weather_stale")

    if inp.ndvi is None:
        reasons.append("missing_ndvi")
    else:
        if inp.valid_pixel_pct is not None and inp.valid_pixel_pct < MIN_VALID_PIXELS:
            reasons.append("low_valid_pixels")
        if inp.ndvi_observed_at:
            age_d = _days_since(inp.ndvi_observed_at)
            if age_d is not None and age_d > MAX_SAT_AGE_DAYS:
                reasons.append("satellite_stale")

    # Missing NDVI alone forces needs_check (MVP rule from docs)
    blocking = {"missing_stage", "missing_irrigation_method", "missing_weather", "weather_stale", "missing_ndvi", "satellite_stale", "low_valid_pixels"}
    if blocking.intersection(reasons):
        return ValidationResult(status="needs_check", reasons=reasons)
    return ValidationResult(status="show_dose", reasons=reasons or ["ok"])


def _hours_since(iso: str) -> float | None:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600.0
    except Exception:
        return None


def _days_since(day: str) -> int | None:
    try:
        d = date.fromisoformat(day[:10])
        return (date.today() - d).days
    except Exception:
        return None
