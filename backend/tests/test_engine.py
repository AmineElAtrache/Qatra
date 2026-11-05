"""Agronomy seat — FAO-56 engine and Open-Meteo parser. Must stay green.

Reference values come from the worked examples of FAO-56
(Allen et al., 1998) so the engine is checked against the book, not itself.
"""

import asyncio

import httpx
import pytest

from app.services.agronomy_service import (
    AgronomyInput,
    compute_etc,
    effective_rain_mm,
    et0_penman_monteith,
    extraterrestrial_radiation,
    fungal_risk,
    readily_available_water,
    root_zone_step,
    run_agronomy,
    spray_volume_liters,
    total_available_water,
    wind_speed_2m,
)
from app.services.weather_service import fetch_weather, parse_open_meteo

MA001 = dict(
    et0_mm_day=4.2,
    stage="fruit_growth",
    irrigation_method="drip",
    effective_rain_mm=1.5,
    wind_kmh=9,
    area_ha=1.2,
)


# --- Locked reference day (docs/contract.json) ------------------------------


def test_etc_315():
    assert compute_etc(4.2, 0.75) == 3.15


def test_same_inputs_same_output():
    a = run_agronomy(AgronomyInput(**MA001))
    b = run_agronomy(AgronomyInput(**MA001))
    assert a == b
    assert a.etc_mm == 3.15
    assert a.kc == 0.75


def test_ma001_dose_and_reasons():
    out = run_agronomy(AgronomyInput(**MA001))
    # net = 3.15 − 1.5 = 1.65 mm ; gross = 1.65 / 0.90 (drip) = 1.83 mm
    assert out.net_irrigation_mm == 1.65
    assert out.gross_irrigation_mm == 1.83
    assert out.reasons == ["fruit_growth", "rain_reduces_need"]
    assert out.spray_blocked is False
    assert out.missing == []


# --- Penman-Monteith against FAO-56 worked examples -------------------------


def test_wind_10m_to_2m_fao_example_14():
    # FAO-56 Example 14: 3.2 m/s at 10 m → 2.4 m/s at 2 m
    assert wind_speed_2m(3.2, 10.0) == pytest.approx(2.4, abs=0.02)


def test_ra_fao_example_8():
    # FAO-56 Example 8: 20°S, 3 September (J = 246) → Ra = 32.2 MJ/m²/day
    assert extraterrestrial_radiation(-20.0, 246) == pytest.approx(32.2, abs=0.1)


def test_et0_fao_example_18_brussels():
    # FAO-56 Example 18: Brussels, 6 July → ET0 = 3.9 mm/day
    et0 = et0_penman_monteith(
        t_max_c=21.5,
        t_min_c=12.3,
        rs_mj=22.07,
        u2_ms=2.078,
        lat_deg=50.80,
        day_of_year=187,
        elevation_m=100,
        rh_max_pct=84,
        rh_min_pct=63,
    )
    assert et0 == pytest.approx(3.9, abs=0.05)


def test_et0_requires_humidity():
    with pytest.raises(ValueError):
        et0_penman_monteith(
            t_max_c=25, t_min_c=12, rs_mj=20, u2_ms=2, lat_deg=34.7, day_of_year=300
        )


# --- Missing data stays missing ---------------------------------------------


def test_missing_et0_gives_no_dose():
    out = run_agronomy(AgronomyInput(**{**MA001, "et0_mm_day": None}))
    assert out.etc_mm is None
    assert out.gross_irrigation_mm is None
    assert "missing_et0" in out.reasons


def test_unknown_stage_is_not_replaced():
    out = run_agronomy(AgronomyInput(**{**MA001, "stage": "harvest_party"}))
    assert out.kc is None
    assert out.gross_irrigation_mm is None
    assert "unknown_stage" in out.reasons


def test_unknown_method_gives_no_gross_dose():
    out = run_agronomy(AgronomyInput(**{**MA001, "irrigation_method": "pivot"}))
    assert out.etc_mm == 3.15
    assert out.gross_irrigation_mm is None
    assert "unknown_irrigation_method" in out.reasons


def test_surface_efficiency():
    out = run_agronomy(AgronomyInput(**{**MA001, "irrigation_method": "surface"}))
    assert out.gross_irrigation_mm == round(1.65 / 0.70, 2)


def test_rain_covers_need():
    out = run_agronomy(AgronomyInput(**{**MA001, "effective_rain_mm": 6.0}))
    assert out.net_irrigation_mm == 0.0
    assert out.gross_irrigation_mm == 0.0


def test_irrigation_already_applied_counts():
    out = run_agronomy(AgronomyInput(**{**MA001, "irrigation_applied_mm": 1.0}))
    assert out.net_irrigation_mm == 0.65


# --- Root-zone balance -------------------------------------------------------


def test_taw_raw_loam_citrus():
    taw = total_available_water("loam")  # 1000 × (0.25 − 0.12) × 1.2
    assert taw == 156.0
    assert readily_available_water(taw) == 78.0


def test_root_zone_step_and_drainage():
    step = root_zone_step(
        depletion_prev_mm=10, etc_mm=3.15, effective_rain_mm=20, net_irrigation_mm=0, taw_mm=156
    )
    assert step.depletion_mm == 0.0
    assert step.deep_percolation_mm == pytest.approx(6.85)


def test_effective_rain_capped_by_room():
    assert effective_rain_mm(None) is None
    assert effective_rain_mm(12.0, max_useful_mm=5.0) == 5.0


def test_root_zone_mode_irrigates_above_raw():
    out = run_agronomy(
        AgronomyInput(**{**MA001, "effective_rain_mm": 0.0, "depletion_prev_mm": 76.0, "soil": "loam"})
    )
    assert out.depletion_mm == 79.15
    assert out.net_irrigation_mm == 79.15
    assert out.gross_irrigation_mm == round(79.15 / 0.90, 2)
    assert "deficit_above_raw" in out.reasons


def test_root_zone_mode_waits_below_raw():
    out = run_agronomy(AgronomyInput(**{**MA001, "depletion_prev_mm": 20.0, "soil": "loam"}))
    assert out.depletion_mm == 21.65
    assert out.gross_irrigation_mm == 0.0
    assert "soil_reserve_ok" in out.reasons


# --- Spraying and fungal risk -----------------------------------------------


def test_wind_blocks_spray():
    out = run_agronomy(AgronomyInput(**{**MA001, "wind_kmh": 16}))
    assert out.spray_blocked is True
    assert out.spray_volume_l is None
    assert "wind_blocks_spray" in out.reasons


def test_wind_limit_is_15():
    assert run_agronomy(AgronomyInput(**{**MA001, "wind_kmh": 14.9})).spray_blocked is False
    assert run_agronomy(AgronomyInput(**{**MA001, "wind_kmh": 15})).spray_blocked is True


def test_unknown_wind_blocks_spray():
    out = run_agronomy(AgronomyInput(**{**MA001, "wind_kmh": None}))
    assert out.spray_blocked is True
    assert "wind_unknown" in out.reasons


def test_spray_volume():
    assert spray_volume_liters(1.2) == 480.0


def test_fungal_risk_rule():
    assert fungal_risk(humidity_pct=88, temperature_c=20, rain_mm=5) == "high"
    assert fungal_risk(humidity_pct=88, temperature_c=20, rain_mm=0) == "medium"
    assert fungal_risk(humidity_pct=45, temperature_c=28, rain_mm=1.5) == "low"
    assert fungal_risk(humidity_pct=None, temperature_c=20, rain_mm=5) is None


# --- Open-Meteo parser (no network) -----------------------------------------

OPEN_METEO_SAMPLE = {
    "latitude": 34.68,
    "longitude": -1.91,
    "elevation": 470.0,
    "utc_offset_seconds": 3600,
    "current": {
        "time": "2026-10-28T13:00",
        "temperature_2m": 24.1,
        "relative_humidity_2m": 41,
        "wind_speed_10m": 11.2,
        "precipitation": 0.0,
    },
    "hourly": {
        "time": [f"2026-10-28T{h:02d}:00" for h in range(24)],
        "relative_humidity_2m": [80] * 6 + [60] * 12 + [35] * 6,
        "wind_speed_10m": [8.0] * 12 + [12.0] * 12,
    },
    "daily": {
        "time": ["2026-10-28"],
        "temperature_2m_max": [25.0],
        "temperature_2m_min": [12.0],
        "precipitation_sum": [0.4],
        "shortwave_radiation_sum": [15.5],
        "et0_fao_evapotranspiration": [3.1],
    },
}


def test_parse_open_meteo_computes_pm_et0():
    obs = parse_open_meteo(OPEN_METEO_SAMPLE, fetched_at="2026-10-28T12:01:00+00:00")
    assert obs.et0_source == "penman_monteith"
    assert obs.et0_mm_day is not None and 1.5 < obs.et0_mm_day < 5.0
    assert obs.observed_at == "2026-10-28T12:00:00+00:00"  # local 13:00, UTC+1
    assert obs.wind_kmh == 11.2
    assert obs.wind_mean_kmh == 10.0
    assert (obs.rh_max_pct, obs.rh_min_pct) == (80.0, 35.0)
    assert obs.rain_mm == 0.4
    assert obs.quality == "live"


def test_parse_open_meteo_falls_back_to_their_et0():
    data = {**OPEN_METEO_SAMPLE, "hourly": {}}
    obs = parse_open_meteo(data)
    assert obs.et0_source == "open_meteo_et0"
    assert obs.et0_mm_day == 3.1


def test_parse_open_meteo_nothing_stays_null():
    obs = parse_open_meteo({})
    assert obs.et0_mm_day is None
    assert obs.observed_at is None
    assert obs.wind_kmh is None


def test_fetch_weather_failure_is_null_not_sample():
    def boom(request):
        raise httpx.ConnectError("offline", request=request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(boom)) as client:
            return await fetch_weather(34.68, -1.91, client=client)

    obs = asyncio.run(run())
    assert obs.quality == "unavailable"
    assert obs.et0_mm_day is None
    assert obs.observed_at is None


def test_fetch_weather_live_path_with_mock():
    async def run():
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=OPEN_METEO_SAMPLE))
        async with httpx.AsyncClient(transport=transport) as client:
            return await fetch_weather(34.68, -1.91, client=client)

    obs = asyncio.run(run())
    assert obs.et0_source == "penman_monteith"
    assert obs.fetched_at is not None


# --- Week 5: explainable fungal risk ------------------------------------------

from datetime import date, datetime, timezone  # noqa: E402

from app.services.agronomy_service import (  # noqa: E402
    fungal_factors,
    replay_input,
    season_start,
    season_totals,
)


def test_fungal_factors_say_why():
    assert fungal_factors(humidity_pct=88, temperature_c=20, rain_mm=5) == [
        "humid_air",
        "mild_temperature",
        "rain_wets_leaves",
    ]
    assert fungal_factors(humidity_pct=45, temperature_c=28, rain_mm=1.5) == ["mild_temperature"]
    assert fungal_factors(humidity_pct=None, temperature_c=20, rain_mm=5) is None


def test_fungal_risk_matches_its_factors():
    out = run_agronomy(AgronomyInput(**{**MA001, "humidity_pct": 88, "temperature_c": 20, "effective_rain_mm": 5}))
    assert out.fungal_risk == "high"
    assert out.fungal_factors == ["humid_air", "mild_temperature", "rain_wets_leaves"]
    assert "fungal_risk_high" in out.reasons


def test_fungal_unknown_without_humidity():
    out = run_agronomy(AgronomyInput(**MA001))
    assert out.fungal_risk is None
    assert out.fungal_factors is None


# --- Week 5: replay -------------------------------------------------------------


def _stored(inp: AgronomyInput) -> dict:
    """What the orchestrator stores for the agronomy part of a payload."""
    out = run_agronomy(inp)
    return {
        "stage": inp.stage,
        "irrigation_method": inp.irrigation_method,
        "area_ha": inp.area_ha,
        "et0_mm_day": inp.et0_mm_day,
        "effective_rain_mm": inp.effective_rain_mm,
        "wind_kmh": inp.wind_kmh,
        "humidity_pct": inp.humidity_pct,
        "temperature_c": inp.temperature_c,
        "etc_mm": out.etc_mm,
        "gross_irrigation_mm": out.gross_irrigation_mm,
        "spray_blocked": out.spray_blocked,
        "fungal_risk": out.fungal_risk,
    }


def test_replay_gives_same_result():
    day = AgronomyInput(**{**MA001, "humidity_pct": 82, "temperature_c": 19})
    stored = _stored(day)
    again = run_agronomy(replay_input(stored))
    assert again.etc_mm == stored["etc_mm"] == 3.15
    assert again.gross_irrigation_mm == stored["gross_irrigation_mm"]
    assert again.spray_blocked == stored["spray_blocked"]
    assert again.fungal_risk == stored["fungal_risk"] == "medium"


def test_replay_of_contract_sample_keeps_etc_315():
    import json
    from pathlib import Path

    contract = Path(__file__).resolve().parents[2] / "docs" / "contract.json"
    payload = json.loads(contract.read_text(encoding="utf-8"))
    assert run_agronomy(replay_input(payload)).etc_mm == 3.15


def test_replay_keeps_missing_inputs_missing():
    again = run_agronomy(replay_input({"stage": "fruit_growth", "irrigation_method": "drip"}))
    assert again.etc_mm is None
    assert again.gross_irrigation_mm is None


# --- Week 5: season totals (campaign from 1 September) ----------------------------


def _day(etc, rain, dose, status="show_dose"):
    return {"etc_mm": etc, "effective_rain_mm": rain, "status": status, "display_dose": dose}


def test_season_starts_on_1_september():
    assert season_start(date(2026, 11, 4)) == date(2026, 9, 1)
    assert season_start(date(2026, 9, 1)) == date(2026, 9, 1)
    assert season_start(date(2026, 8, 31)) == date(2025, 9, 1)
    assert season_start(date(2027, 1, 15)) == date(2026, 9, 1)


def test_season_totals_add_up():
    records = [
        ("2026-11-01", _day(2.0, 0.0, 2.2)),
        ("2026-11-02", _day(1.8, 1.5, 0.3)),
        ("2026-11-03", _day(2.1, 0.0, 2.3)),
    ]
    s = season_totals(records, today=date(2026, 11, 4), area_ha=1.2)
    assert s.season_start == "2026-09-01"
    assert s.days_counted == 3
    assert s.etc_mm == 5.9
    assert s.rain_mm == 1.5
    assert s.water_advised_mm == 4.8
    assert s.water_advised_m3 == 57.6  # 4.8 mm × 1.2 ha × 10


def test_season_counts_one_calculation_per_day():
    records = [
        (datetime(2026, 11, 2, 8, tzinfo=timezone.utc), _day(9.0, 0.0, 9.0)),
        (datetime(2026, 11, 2, 10, tzinfo=timezone.utc), _day(1.8, 1.5, 0.3)),
    ]
    s = season_totals(records, today=date(2026, 11, 4), area_ha=1.0)
    assert s.days_counted == 1
    assert s.etc_mm == 1.8
    assert s.water_advised_mm == 0.3


def test_season_ignores_previous_season_and_future():
    records = [
        ("2026-08-31", _day(50.0, 0.0, 50.0)),  # last day of 2025-26 campaign
        ("2026-09-01", _day(3.0, 0.0, 3.3)),
        ("2026-11-05", _day(50.0, 0.0, 50.0)),  # after today
    ]
    s = season_totals(records, today=date(2026, 11, 4), area_ha=1.0)
    assert s.days_counted == 1
    assert s.etc_mm == 3.0


def test_season_needs_check_days_add_no_water():
    records = [
        ("2026-11-01", _day(2.0, 0.0, 2.2)),
        ("2026-11-02", _day(1.8, 0.0, None, status="needs_check")),
    ]
    s = season_totals(records, today=date(2026, 11, 4), area_ha=1.0)
    assert s.etc_mm == 3.8  # the need is still counted
    assert s.water_advised_mm == 2.2  # only the dose actually shown


def test_season_missing_etc_is_counted_not_invented():
    records = [
        ("2026-11-01", _day(2.0, 0.0, 2.2)),
        ("2026-11-02", _day(None, None, None, status="needs_check")),
    ]
    s = season_totals(records, today=date(2026, 11, 4), area_ha=1.0)
    assert s.days_counted == 2
    assert s.days_missing_etc == 1
    assert s.etc_mm == 2.0


def test_season_without_data_stays_null():
    s = season_totals([], today=date(2026, 11, 4), area_ha=1.2)
    assert s.days_counted == 0
    assert (s.etc_mm, s.rain_mm, s.water_advised_mm, s.water_advised_m3) == (None, None, None, None)


def test_season_without_area_has_no_m3():
    s = season_totals([("2026-11-01", _day(2.0, 0.0, 2.2))], today=date(2026, 11, 4), area_ha=None)
    assert s.water_advised_mm == 2.2
    assert s.water_advised_m3 is None
