"""Agronomy seat — Open-Meteo client.

- ET0 is computed here with FAO-56 Penman-Monteith from Open-Meteo inputs
  (source ``penman_monteith``). If an input is missing, Open-Meteo's own
  FAO ET0 is used (source ``open_meteo_et0``). If both are missing: None.
- ``observed_at`` is the time Open-Meteo reports (UTC), not the server clock.
- If the call fails, every value stays None (quality ``unavailable``), so the
  validator answers ``needs_check``. Nothing is invented.
- ``sample_weather()`` is the contract sample for tests and offline demos only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.services.agronomy_service import et0_penman_monteith, kmh_to_ms, wind_speed_2m

DAILY_VARS = (
    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "shortwave_radiation_sum,et0_fao_evapotranspiration"
)
HOURLY_VARS = "relative_humidity_2m,wind_speed_10m"
CURRENT_VARS = "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"


@dataclass
class WeatherObservation:
    temperature_c: float | None
    humidity_pct: float | None
    wind_kmh: float | None  # current wind at 10 m (spraying)
    rain_mm: float | None  # rain of the day (observed + forecast)
    radiation_mj: float | None
    et0_mm_day: float | None
    et0_source: str | None
    observed_at: str | None  # Open-Meteo time, ISO UTC
    quality: str  # live | sample | unavailable
    # Daily inputs kept for audit / replay
    t_max_c: float | None = None
    t_min_c: float | None = None
    rh_max_pct: float | None = None
    rh_min_pct: float | None = None
    wind_mean_kmh: float | None = None
    elevation_m: float | None = None
    et0_open_meteo_mm: float | None = None
    fetched_at: str | None = None
    source: str = "open-meteo"
    reason: str | None = None


async def fetch_weather(
    lat: float,
    lon: float,
    *,
    client: httpx.AsyncClient | None = None,
) -> WeatherObservation:
    """Live Open-Meteo forecast for today. Never raises."""
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": CURRENT_VARS,
        "hourly": HOURLY_VARS,
        "daily": DAILY_VARS,
        "timezone": "auto",
        "forecast_days": 1,
        "wind_speed_unit": "kmh",
    }
    url = f"{settings.open_meteo_base_url}/forecast"
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.get(url, params=params)
        else:
            r = await client.get(url, params=params)
        r.raise_for_status()
        return parse_open_meteo(r.json(), fetched_at=fetched_at)
    except Exception as exc:  # network, HTTP or schema error
        return missing_weather(reason=f"open_meteo_error:{type(exc).__name__}", fetched_at=fetched_at)


def parse_open_meteo(data: dict[str, Any], *, fetched_at: str | None = None) -> WeatherObservation:
    """Pure parser: Open-Meteo JSON → observation. Testable without network."""
    current = data.get("current") or {}
    daily = data.get("daily") or {}
    hourly = data.get("hourly") or {}
    offset = int(data.get("utc_offset_seconds") or 0)

    t_max = _first(daily.get("temperature_2m_max"))
    t_min = _first(daily.get("temperature_2m_min"))
    rs = _first(daily.get("shortwave_radiation_sum"))
    rain = _first(daily.get("precipitation_sum"))
    et0_om = _first(daily.get("et0_fao_evapotranspiration"))
    day = _first(daily.get("time"))

    rh = _clean(hourly.get("relative_humidity_2m"))
    wind_h = _clean(hourly.get("wind_speed_10m"))
    rh_max = max(rh) if rh else None
    rh_min = min(rh) if rh else None
    wind_mean = round(sum(wind_h) / len(wind_h), 2) if wind_h else None

    lat = data.get("latitude")
    elevation = data.get("elevation")

    et0: float | None = None
    source: str | None = None
    if None not in (t_max, t_min, rs, rh_max, rh_min, wind_mean, lat, day):
        et0 = et0_penman_monteith(
            t_max_c=t_max,
            t_min_c=t_min,
            rs_mj=rs,
            u2_ms=wind_speed_2m(kmh_to_ms(wind_mean), 10.0),
            lat_deg=float(lat),
            day_of_year=date.fromisoformat(day).timetuple().tm_yday,
            elevation_m=float(elevation or 0.0),
            rh_max_pct=rh_max,
            rh_min_pct=rh_min,
        )
        source = "penman_monteith"
    elif et0_om is not None:
        et0 = round(float(et0_om), 2)
        source = "open_meteo_et0"

    return WeatherObservation(
        temperature_c=current.get("temperature_2m"),
        humidity_pct=current.get("relative_humidity_2m"),
        wind_kmh=_float(current.get("wind_speed_10m")),
        rain_mm=_float(rain),
        radiation_mj=_float(rs),
        et0_mm_day=et0,
        et0_source=source,
        observed_at=_to_utc_iso(current.get("time"), offset),
        quality="live" if et0 is not None else "partial",
        t_max_c=t_max,
        t_min_c=t_min,
        rh_max_pct=rh_max,
        rh_min_pct=rh_min,
        wind_mean_kmh=wind_mean,
        elevation_m=_float(elevation),
        et0_open_meteo_mm=_float(et0_om),
        fetched_at=fetched_at,
        reason=None if et0 is not None else "et0_inputs_missing",
    )


def missing_weather(reason: str = "unavailable", fetched_at: str | None = None) -> WeatherObservation:
    """Honest empty observation: every value None → validator says needs_check."""
    return WeatherObservation(
        temperature_c=None,
        humidity_pct=None,
        wind_kmh=None,
        rain_mm=None,
        radiation_mj=None,
        et0_mm_day=None,
        et0_source=None,
        observed_at=None,
        quality="unavailable",
        fetched_at=fetched_at,
        reason=reason,
    )


def sample_weather() -> WeatherObservation:
    """Contract sample (MA-001) — tests and offline demo only, flagged as sample."""
    return WeatherObservation(
        temperature_c=28.0,
        humidity_pct=45.0,
        wind_kmh=9.0,
        rain_mm=1.5,
        radiation_mj=22.0,
        et0_mm_day=4.2,
        et0_source="penman_monteith",
        observed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        quality="sample",
    )


# --- helpers ---------------------------------------------------------------


def _first(values: Any) -> Any:
    if isinstance(values, list) and values:
        return values[0]
    return None


def _clean(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    return [float(v) for v in values if v is not None]


def _float(v: Any) -> float | None:
    return float(v) if v is not None else None


def _to_utc_iso(local_time: str | None, offset_seconds: int) -> str | None:
    """Open-Meteo gives local time + offset; return ISO UTC."""
    if not local_time:
        return None
    try:
        local = datetime.fromisoformat(local_time)
    except ValueError:
        return None
    return (local - timedelta(seconds=offset_seconds)).replace(tzinfo=timezone.utc).isoformat()
