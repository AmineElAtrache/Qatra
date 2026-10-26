"""Backend seat — validator rules."""

from app.services.validator import ValidationInput, validate


def test_missing_ndvi_needs_check():
    result = validate(
        ValidationInput(
            stage="fruit_growth",
            irrigation_method="drip",
            weather_observed_at="2099-01-01T12:00:00+00:00",
            ndvi=None,
            ndvi_observed_at=None,
            valid_pixel_pct=None,
        )
    )
    assert result.status == "needs_check"
    assert "missing_ndvi" in result.reasons


def test_old_satellite_needs_check():
    result = validate(
        ValidationInput(
            stage="fruit_growth",
            irrigation_method="drip",
            weather_observed_at="2099-01-01T12:00:00+00:00",
            ndvi=0.5,
            ndvi_observed_at="2020-01-01",
            valid_pixel_pct=90,
        )
    )
    assert result.status == "needs_check"
    assert "satellite_stale" in result.reasons
