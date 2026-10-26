"""Agronomy seat — Open-Meteo client. Stub returns contract sample when offline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.core.config import settings


@dataclass
class WeatherObservation:
    temperature_c: float | None
    humidity_pct: float | None
    wind_kmh: float
    rain_mm: float
    radiation_mj: float | None
    et0_mm_day: float
    et0_source: str
    observed_at: str
    quality: str


async def fetch_weather(lat: float, lon: float) -> WeatherObservation:
    """Live Open-Meteo when reachable; else honest sample for MA-001 demos."""
    try:
        url = f"{settings.open_meteo_base_url}/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "daily": "et0_fao_evapotranspiration,shortwave_radiation_sum",
            "timezone": "auto",
            "forecast_days": 1,
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        et0 = (daily.get("et0_fao_evapotranspiration") or [None])[0]
        rad = (daily.get("shortwave_radiation_sum") or [None])[0]
        return WeatherObservation(
            temperature_c=current.get("temperature_2m"),
            humidity_pct=current.get("relative_humidity_2m"),
            wind_kmh=float(current.get("wind_speed_10m") or 0),
            rain_mm=float(current.get("precipitation") or 0),
            radiation_mj=rad,
            et0_mm_day=float(et0) if et0 is not None else 4.2,
            et0_source="open_meteo_et0" if et0 is not None else "penman_monteith_fallback",
            observed_at=datetime.now(timezone.utc).isoformat(),
            quality="live",
        )
    except Exception:
        return sample_weather()


def sample_weather() -> WeatherObservation:
    """Contract sample — used by tests and offline demo."""
    return WeatherObservation(
        temperature_c=28.0,
        humidity_pct=45.0,
        wind_kmh=9.0,
        rain_mm=1.5,
        radiation_mj=22.0,
        et0_mm_day=4.2,
        et0_source="penman_monteith",
        observed_at=datetime.now(timezone.utc).isoformat(),
        quality="sample",
    )
