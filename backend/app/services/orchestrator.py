"""Backend seat — calls agents in order. No dose invented here."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.geo import centroid_lon_lat, default_ma001_geojson
from app.services import agronomy_service, explain, notification, satellite_service, validator, weather_service
from app.services.agronomy_service import AgronomyInput


async def run_recommendation(
    *,
    plot_id: str,
    crop: str,
    stage: str,
    irrigation_method: str,
    area_ha: float,
    geojson: dict[str, Any] | None = None,
    lat: float | None = None,
    lon: float | None = None,
    notify: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parcel = geojson or default_ma001_geojson()
    center = centroid_lon_lat(parcel)
    if lon is None or lat is None:
        if center:
            lon, lat = center
        else:
            lon, lat = -7.5898, 33.5731

    weather = await weather_service.fetch_weather(lat, lon)
    sat = await satellite_service.fetch_indices(geojson=parcel)
    sat = satellite_service.maybe_sentinel1_fallback(sat)
    if sat.ndvi is None and settings.satellite_demo_fallback:
        from datetime import date

        sat = satellite_service.sample_optical()
        sat.ndvi_observed_at = date.today().isoformat()
        sat.quality = "demo_sample"
        sat.reason = "gee_unavailable_demo_fallback"

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
        "lat": lat,
        "lon": lon,
    }
    payload.update(sat.to_contract_dict())

    if decision.status != "show_dose":
        payload["display_dose"] = None
    else:
        payload["display_dose"] = agro.gross_irrigation_mm

    payload["texts"] = await explain.explain(payload)

    if notify and notify.get("opt_in"):
        text = (payload.get("texts") or {}).get("fr") or (payload.get("texts") or {}).get("darija") or ""
        payload["notification"] = await notification.notify_farmer(
            channel=notify.get("channel"),
            telegram_chat_id=notify.get("telegram_chat_id"),
            text=text,
        )

    return payload
