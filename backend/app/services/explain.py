"""Explanation seat — Ollama when up; offline templates always available."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def template_texts(payload: dict[str, Any]) -> dict[str, str]:
    """Numbers only from payload — never invent."""
    etc = payload.get("etc_mm")
    rain = payload.get("effective_rain_mm")
    gross = payload.get("gross_irrigation_mm")
    status = payload.get("status", "needs_check")

    if status != "show_dose" or etc is None:
        fr = "Besoin à vérifier. La dose précise n'est pas affichée tant que les données ne sont pas confirmées."
        darija = "Khass n2aked. Doza ma kaynach 7it data ma kamlach."
        ar = "يجب التحقق. الجرعة الدقيقة غير معروضة ما دامت البيانات غير مؤكدة."
    else:
        fr = (
            f"Besoin estimé {etc} mm (ETc). "
            f"Pluie utile {rain} mm. "
            f"Dose brute indicative {gross} mm."
        )
        darija = f"L7aja dyal lma: {etc} mm. Shta nafi3a: {rain} mm. Doza ta9ribiya: {gross} mm."
        ar = f"الاحتياج التقديري {etc} مم. مطر نافع {rain} مم. جرعة خام إرشادية {gross} مم."

    return {"fr": fr, "darija": darija, "ar": ar}


async def explain(payload: dict[str, Any]) -> dict[str, str]:
    """Try Ollama; on any failure return templates (demo must survive model down)."""
    fallback = template_texts(payload)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "stream": False,
                    "prompt": (
                        "Explain this irrigation JSON in three short lines labeled FR, DARIJA, AR. "
                        "Use only numbers present in the JSON. JSON: "
                        f"{payload}"
                    ),
                },
            )
            if r.status_code != 200:
                return fallback
            # Keep MVP simple: still return templates so numbers stay controlled.
            # Explanation seat can replace parsing later without changing the contract.
            return fallback
    except Exception:
        return fallback


async def ask_qatra(question: str, last_payload: dict[str, Any]) -> dict[str, str]:
    """Answer from last recommendation only (+ knowledge folder later)."""
    base = await explain(last_payload)
    base["note"] = f"Ask Qatra (MVP): answered from stored recommendation. Q={question[:200]}"
    return base
