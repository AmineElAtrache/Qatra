from datetime import date, datetime, timezone

import pytest

from app.services.validator import ValidationInput, validate


def valid_input(**changes):
    data = dict(stage="fruit_growth", irrigation_method="drip", et0_mm_day=4.2,
                weather_observed_at=datetime.now(timezone.utc).isoformat(), ndvi=0.68,
                ndvi_observed_at=date.today().isoformat(), valid_pixel_pct=86)
    return ValidationInput(**(data | changes))


def test_valid_observations_allow_dose():
    assert validate(valid_input()).status == "show_dose"


@pytest.mark.parametrize("changes", [
    {"stage": "unknown"}, {"irrigation_method": "unknown"},
    {"weather_observed_at": "invalid"}, {"weather_observed_at": "2099-01-01"},
    {"ndvi_observed_at": None}, {"ndvi_observed_at": "invalid"},
    {"ndvi_observed_at": "2099-01-01"}, {"valid_pixel_pct": None},
    {"valid_pixel_pct": 69.9}, {"valid_pixel_pct": float("nan")},
    {"ndvi": float("nan")}, {"et0_mm_day": None}, {"et0_mm_day": float("nan")},
])
def test_incomplete_or_invalid_observations_hide_dose(changes):
    assert validate(valid_input(**changes)).status == "needs_check"
