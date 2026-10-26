"""Agronomy seat — locked FAO-56 sample. Must stay green."""

from app.services.agronomy_service import (
    AgronomyInput,
    compute_etc,
    run_agronomy,
    spray_volume_liters,
)


def test_etc_315():
    assert compute_etc(4.2, 0.75) == 3.15


def test_same_inputs_same_output():
    inp = AgronomyInput(
        et0_mm_day=4.2,
        stage="fruit_growth",
        irrigation_method="drip",
        effective_rain_mm=1.5,
        wind_kmh=9,
        area_ha=1.2,
    )
    a = run_agronomy(inp)
    b = run_agronomy(inp)
    assert a == b
    assert a.etc_mm == 3.15


def test_wind_blocks_spray():
    inp = AgronomyInput(
        et0_mm_day=4.2,
        stage="fruit_growth",
        irrigation_method="drip",
        wind_kmh=16,
    )
    out = run_agronomy(inp)
    assert out.spray_blocked is True
    assert "wind_blocks_spray" in out.reasons


def test_spray_volume():
    assert spray_volume_liters(1.2) == 480.0
