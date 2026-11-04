"""Backend seat — decide show_dose vs needs_check. Never invent numbers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from app.services.agronomy_service import kc_for_stage, efficiency


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
    et0_mm_day: float | None = None


@dataclass
class ValidationResult:
    status: str  # show_dose | needs_check
    reasons: list[str]


def validate(inp: ValidationInput) -> ValidationResult:
    reasons: list[str] = []

    if kc_for_stage(inp.stage) is None:
        reasons.append("missing_stage")
    if efficiency(inp.irrigation_method) is None:
        reasons.append("missing_irrigation_method")

    if not inp.weather_observed_at:
        reasons.append("missing_weather")
    else:
        age_h = _hours_since(inp.weather_observed_at)
        if age_h is None or age_h < 0:
            reasons.append("invalid_weather_date")
        elif age_h > MAX_WEATHER_AGE_HOURS:
            reasons.append("weather_stale")
    if inp.et0_mm_day is None or not isfinite(inp.et0_mm_day) or inp.et0_mm_day < 0:
        reasons.append("missing_et0")

    if inp.ndvi is None:
        reasons.append("missing_ndvi")
    else:
        if not isfinite(inp.ndvi) or not -1 <= inp.ndvi <= 1:
            reasons.append("invalid_ndvi")
        if inp.valid_pixel_pct is None or not isfinite(inp.valid_pixel_pct) or not MIN_VALID_PIXELS <= inp.valid_pixel_pct <= 100:
            reasons.append("low_valid_pixels")
        if inp.ndvi_observed_at:
            age_d = _days_since(inp.ndvi_observed_at)
            if age_d is None or age_d < 0:
                reasons.append("invalid_satellite_date")
            elif age_d > MAX_SAT_AGE_DAYS:
                reasons.append("satellite_stale")
        else:
            reasons.append("missing_satellite_date")

    # Missing NDVI alone forces needs_check (MVP rule from docs)
    if reasons:
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
