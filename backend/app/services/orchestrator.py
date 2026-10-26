"""Backend seat — calls agents in order. No dose invented here."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services import agronomy_service, explain, satellite_service, validator, weather_service
from app.services.agronomy_service import AgronomyInput


async def run_recommendation(
    *,
    plot_id: str,
    crop: str,
    stage: str,
    irrigation_method: str,
    area_ha: float,
    lat: float = 33.5731,
    lon: float = -7.5898,
) -> dict[str, Any]:
    weather = await weather_service.fetch_weather(lat, lon)
    sat = await satellite_service.fetch_indices()
    sat = satellite_service.maybe_sentinel1_fallback(sat)

    agro = agronomy_service.run_agronomy(
        AgronomyInput(
            et0_mm_day=weather.et0_mm_day,
            stage=stage,
            irrigation_method=irrigation_method,
            effective_rain_mm=weather.rain_mm,
            wind_kmh=weather.wind_kmh,
            area_ha=area_ha,
        )
    )

    decision = validator.validate(
        validator.ValidationInput(
            stage=stage,
            irrigation_method=irrigation_method,
            weather_observed_at=weather.observed_at,
            ndvi=sat.ndvi,
            ndvi_observed_at=sat.ndvi_observed_at,
            valid_pixel_pct=sat.valid_pixel_pct,
        )
    )

    payload: dict[str, Any] = {
        "plot_id": plot_id,
        "crop": crop,
        "stage": stage,
        "area_ha": area_ha,
        "irrigation_method": irrigation_method,
        "et0_mm_day": weather.et0_mm_day,
        "et0_source": weather.et0_source,
        "kc": agro.kc,
        "etc_mm": agro.etc_mm,
        "effective_rain_mm": weather.rain_mm,
        "gross_irrigation_mm": agro.gross_irrigation_mm,
        "ndvi": sat.ndvi,
        "ndwi": sat.ndwi,
        "ndvi_observed_at": sat.ndvi_observed_at,
        "valid_pixel_pct": sat.valid_pixel_pct,
        "satellite_source": sat.satellite_source,
        "wind_kmh": weather.wind_kmh,
        "spray_blocked": agro.spray_blocked,
        "disease_risk": agro.disease_risk,
        "fungal_risk": agro.fungal_risk,
        "status": decision.status,
        "reasons": list(dict.fromkeys(agro.reasons + decision.reasons)),
        "engine_version": settings.engine_version,
        "weather_observed_at": weather.observed_at,
        "weather_quality": weather.quality,
        "satellite_quality": sat.quality,
    }

    # Hide precise dose presentation when needs_check (values stay in payload for audit)
    if decision.status != "show_dose":
        payload["display_dose"] = None
    else:
        payload["display_dose"] = agro.gross_irrigation_mm

    payload["texts"] = await explain.explain(payload)
    return payload
