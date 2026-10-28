"""Explanation seat — Ask Qatra interactive assistant (web + WhatsApp)."""

import asyncio

from app.services.explain import ask_qatra


def _payload() -> dict:
    return {
        "status": "show_dose",
        "display_dose": 4.7,
        "etc_mm": 3.15,
        "effective_rain_mm": 1.5,
        "gross_irrigation_mm": 4.7,
        "irrigation_method": "drip",
        "crop": "citrus",
        "fungal_risk": "medium",
        "spray_blocked": False,
        "wind_kmh": 9,
    }


def test_ask_qatra_returns_three_languages():
    out = asyncio.run(ask_qatra("Besoin irrigation ?", _payload()))
    assert set(out) >= {"fr", "ar", "darija", "answer", "note"}
    assert "3.15" in out["fr"] or "3,15" in out["fr"]
    assert "4.7" in out["fr"] or "4,7" in out["fr"]


def test_ask_qatra_irrigation_question():
    out = asyncio.run(ask_qatra("How much water today?", _payload()))
    assert "3.15" in out["answer"] or "3,15" in out["answer"]
    assert "4.7" in out["answer"] or "4,7" in out["answer"]


def test_ask_qatra_risk_question():
    out = asyncio.run(ask_qatra("Risque fongique ?", _payload()))
    assert "medium" in out["answer"].lower() or "modéré" in out["answer"].lower()


def test_ask_qatra_spray_question():
    out = asyncio.run(ask_qatra("Spray blocked?", _payload()))
    assert "False" in out["answer"] or "false" in out["answer"]


def test_ask_qatra_needs_check_payload():
    out = asyncio.run(ask_qatra("Que faire ?", {"status": "needs_check"}))
    assert set(out) >= {"fr", "ar", "darija"}
    assert "3.15" not in out["fr"]


def test_ask_qatra_grounds_in_knowledge_folder():
    out = asyncio.run(ask_qatra("Irrigation rules FAO", _payload()))
    # The answer references at least one knowledge page.
    assert "Reference:" in out["answer"]