"""Explanation seat — templates work with model cut."""

import asyncio

from app.services.explain import explain, template_texts


def test_templates_have_three_languages():
    texts = template_texts(
        {
            "status": "show_dose",
            "display_dose": 4.7,
            "etc_mm": 3.15,
            "effective_rain_mm": 1.5,
            "gross_irrigation_mm": 4.7,
        }
    )
    assert "3.15" in texts["fr"] or "3,15" in texts["fr"]
    assert "darija" in texts and "ar" in texts


def test_explain_survives_ollama_down():
    payload = {"status": "needs_check"}
    out = asyncio.run(explain(payload))
    assert set(out) >= {"fr", "darija", "ar"}
