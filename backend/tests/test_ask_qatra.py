"""Explanation seat — Ask Qatra interactive assistant (web + WhatsApp)."""

import asyncio
import re

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
    assert set(out) >= {"en", "fr", "ar", "darija", "answer", "note", "language"}
    assert "3.15" in out["fr"] or "3,15" in out["fr"]
    assert "4.7" in out["fr"] or "4,7" in out["fr"]


def test_ask_qatra_irrigation_question():
    out = asyncio.run(ask_qatra("How much water today?", _payload()))
    assert out["language"] == "en"
    assert "3.15" in out["answer"] or "3,15" in out["answer"]
    assert "4.7" in out["answer"] or "4,7" in out["answer"]


def test_ask_qatra_risk_question():
    out = asyncio.run(ask_qatra("Risque fongique ?", _payload()))
    assert "medium" in out["answer"].lower() or "modéré" in out["answer"].lower()


def test_ask_qatra_spray_question():
    out = asyncio.run(ask_qatra("Spray blocked?", _payload()))
    assert "does not block spraying" in out["answer"]


def test_ask_qatra_needs_check_payload():
    out = asyncio.run(ask_qatra("Que faire ?", {"status": "needs_check"}))
    assert set(out) >= {"en", "fr", "ar", "darija"}
    assert "3.15" not in out["fr"]
    assert " mm" not in out["answer"]


def test_ask_qatra_grounds_in_knowledge_folder():
    out = asyncio.run(ask_qatra("Irrigation rules FAO", _payload()))
    assert "Référence (FAO):" in out["answer"]


def test_ask_qatra_localizes_from_question():
    french = asyncio.run(ask_qatra("Quel besoin en eau ?", _payload()))
    arabic = asyncio.run(ask_qatra("ما كمية ماء الري؟", _payload()))
    assert french["language"] == "fr"
    assert french["answer"].startswith("Valeurs d'irrigation")
    assert arabic["language"] == "ar"
    assert arabic["answer"].startswith("قيم الري")


def test_ask_qatra_honors_explicit_language():
    out = asyncio.run(ask_qatra("How much water?", _payload(), language="fr"))
    assert out["language"] == "fr"
    assert out["answer"].startswith("Valeurs d'irrigation")


def test_ask_qatra_omits_missing_metrics():
    payload = {"status": "show_dose"}
    out = asyncio.run(ask_qatra("How much water today?", payload))
    assert "None" not in out["answer"]
    assert re.search(r"\d+(?:\.\d+)?\s*mm", out["answer"]) is None


def test_ask_qatra_answers_risk_without_inventing_irrigation_amount():
    state = {"status": "needs_check", "fungal_risk": "high"}
    out = asyncio.run(ask_qatra("Is there a disease risk?", state))
    assert "Fungal risk is high" in out["answer"]
    assert re.search(r"\d+(?:\.\d+)?\s*mm", out["answer"]) is None


def test_ask_qatra_reads_nested_state_without_estimating():
    state = {
        "crop_type": "Olive",
        "irrigation_recommendation": {
            "action": "IRRIGATE",
            "water_volume_mm": 4.5,
        },
    }
    out = asyncio.run(ask_qatra("How much water?", state))
    assert "4.5 mm" in out["answer"]
    assert re.findall(r"(?<![\w.])\d+(?:\.\d+)? mm", out["answer"]) == ["4.5 mm"]


def test_ask_qatra_reads_last_stored_json_state(tmp_path, monkeypatch):
    from app.services import explain

    state_path = tmp_path / "last_stored_state.json"
    state_path.write_text(
        '{"status":"show_dose","display_dose":4.7,"gross_irrigation_mm":4.7}'
    )
    monkeypatch.setattr(explain.settings, "last_stored_state_path", str(state_path))
    out = asyncio.run(ask_qatra("How much water today?"))
    assert "4.7 mm" in out["answer"]


def test_state_round_trip(tmp_path, monkeypatch):
    from app.services import explain

    state_path = tmp_path / "last_stored_state.json"
    monkeypatch.setattr(explain.settings, "last_stored_state_path", str(state_path))
    payload = _payload()
    explain.save_last_stored_state(payload)
    assert explain.load_last_stored_state() == payload
