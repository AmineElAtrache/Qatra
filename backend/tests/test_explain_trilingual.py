"""Explanation seat — trilingual engine (FR, AR, Darija) on live payloads."""

from app.services.explain import template_texts


def test_three_languages_on_live_payload():
    """The engine reads the orchestrator's live contract schema."""
    payload = {
        "plot_id": "MA-001",
        "crop": "citrus",
        "stage": "fruit_growth",
        "irrigation_method": "drip",
        "et0_mm_day": 4.2,
        "etc_mm": 3.15,
        "effective_rain_mm": 1.5,
        "gross_irrigation_mm": 4.7,
        "wind_kmh": 9,
        "spray_blocked": False,
        "disease_risk": "medium",
        "fungal_risk": "medium",
        "status": "show_dose",
        "display_dose": 4.7,
    }

    texts = template_texts(payload)

    assert set(texts) == {"fr", "ar", "darija"}
    # Only numbers that exist in the payload are ever emitted.
    assert "3.15" in texts["fr"] or "3,15" in texts["fr"]
    assert "4.7" in texts["fr"] or "4,7" in texts["fr"]
    assert "1.5" in texts["fr"] or "1,5" in texts["fr"]
    # No invented number (e.g. 5.0 must not appear).
    assert "5.0" not in texts["fr"]


def test_three_languages_when_spray_blocked():
    payload = {
        "status": "show_dose",
        "display_dose": 4.7,
        "etc_mm": 3.15,
        "effective_rain_mm": 1.5,
        "gross_irrigation_mm": 4.7,
        "spray_blocked": True,
        "fungal_risk": "high",
    }
    texts = template_texts(payload)
    assert set(texts) == {"fr", "ar", "darija"}
    assert "pulvérisation" in texts["fr"].lower() or "vent" in texts["fr"].lower()


def test_three_languages_on_needs_check():
    payload = {"status": "needs_check"}
    texts = template_texts(payload)
    assert set(texts) == {"fr", "ar", "darija"}
    # No dose number leaked when the dose is hidden.
    assert "3.15" not in texts["fr"]


def test_trilingual_survives_ollama_down():
    payload = {
        "status": "show_dose",
        "display_dose": 4.7,
        "etc_mm": 3.15,
        "effective_rain_mm": 1.5,
        "gross_irrigation_mm": 4.7,
    }
    out = template_texts(payload)
    assert set(out) == {"fr", "ar", "darija"}