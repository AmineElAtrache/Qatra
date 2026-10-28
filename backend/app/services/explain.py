"""Explanation seat — offline template engine with FAO/INRA reference folder.

The templates are the fallback when the language model is down. They only
restitute numbers that already exist in the payload. The knowledge folder
(`backend/knowledge/fao`, `backend/knowledge/inra`) holds the reference pages
the explanation may quote; they never replace the formula in code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings


# ---------------------------------------------------------------------------
# Knowledge folder loading
# ---------------------------------------------------------------------------
def knowledge_dir() -> Path:
    """Resolve the knowledge folder relative to the backend package."""
    base = Path(settings.knowledge_dir)
    if base.is_absolute():
        return base
    # settings.knowledge_dir is "knowledge" → resolve against backend/
    return Path(__file__).resolve().parents[2] / base


def list_reference_pages() -> list[Path]:
    """Return every markdown page found under the FAO/INRA knowledge folder."""
    root = knowledge_dir()
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def load_reference() -> str:
    """Concatenate the knowledge pages into one searchable blob."""
    return "\n\n---\n\n".join(p.read_text(encoding="utf-8") for p in list_reference_pages())


# ---------------------------------------------------------------------------
# Field normalisation — accept both the contract schema and older aliases
# ---------------------------------------------------------------------------
def _get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for k in keys:
        if k in data and data[k] is not None:
            return data[k]
    return default


def _status(data: dict[str, Any]) -> str:
    return str(_get(data, "status", "needs_check")).lower()


def _show_dose(data: dict[str, Any]) -> bool:
    return _status(data) == "show_dose" and _get(data, "display_dose") is not None


# ---------------------------------------------------------------------------
# Template builders — one per language, all driven by the same payload
# ---------------------------------------------------------------------------
def _fr(data: dict[str, Any]) -> str:
    parts: list[str] = []

    if not _show_dose(data):
        return (
            "Besoin à vérifier. La dose précise n'est pas affichée tant que "
            "les données ne sont pas confirmées."
        )

    etc = _get(data, "etc_mm")
    rain = _get(data, "effective_rain_mm", 0.0)
    gross = _get(data, "gross_irrigation_mm")
    method = _get(data, "irrigation_method", "")
    crop = _get(data, "crop", "culture")

    parts.append(
        f"Besoin estimé {etc} mm (ETc) pour votre {crop}. "
        f"Pluie utile {rain} mm. Dose brute indicative {gross} mm."
    )
    if method:
        parts.append(f"Irrigation par {method}.")

    fungal = _get(data, "fungal_risk", _get(data, "disease_risk", "low"))
    if fungal == "high":
        parts.append("Risque fongique élevé, restez vigilant.")
    elif fungal == "medium":
        parts.append("Risque fongique modéré, surveillance conseillée.")

    if _get(data, "spray_blocked"):
        parts.append("Traitement par pulvérisation bloqué aujourd'hui (vent fort).")

    return " ".join(parts)


def _ar(data: dict[str, Any]) -> str:
    parts: list[str] = []

    if not _show_dose(data):
        return "يجب التحقق. الجرعة الدقيقة غير معروضة ما دامت البيانات غير مؤكدة."

    etc = _get(data, "etc_mm")
    rain = _get(data, "effective_rain_mm", 0.0)
    gross = _get(data, "gross_irrigation_mm")
    crop = _get(data, "crop", "المحصول")

    parts.append(
        f"الاحتياج التقديري {etc} مم (ETc) لـ {crop}. "
        f"مطر نافع {rain} مم. جرعة خام إرشادية {gross} مم."
    )

    fungal = _get(data, "fungal_risk", _get(data, "disease_risk", "low"))
    if fungal == "high":
        parts.append("انتبه، خطر الأمراض (الفطريات) مرتفع بسبب الرطوبة.")
    elif fungal == "medium":
        parts.append("يوجد خطر متوسط للمرض، المراقبة موصى بها.")

    if _get(data, "spray_blocked"):
        parts.append("العلاج بالرش ممنوع اليوم بسبب الريح القوي.")

    return " ".join(parts)


def _darija(data: dict[str, Any]) -> str:
    parts: list[str] = []

    if not _show_dose(data):
        return "Khass n2aked. Doza ma kaynach 7it data ma kamlach."

    etc = _get(data, "etc_mm")
    rain = _get(data, "effective_rain_mm", 0.0)
    gross = _get(data, "gross_irrigation_mm")
    method = _get(data, "irrigation_method", "")

    parts.append(
        f"L7aja dyal lma: {etc} mm. Shta nafi3a: {rain} mm. Doza ta9ribiya: {gross} mm."
    )
    if method:
        parts.append(f"Irrigation: {method}.")

    fungal = _get(data, "fungal_risk", _get(data, "disease_risk", "low"))
    if fungal == "high":
        parts.append("رد بالك، كاين خطر مرتفع ديال الفطريات والبياض.")
    elif fungal == "medium":
        parts.append("كاين شوية الخطر ديال الفطريات، حاول تراقب الشجر ديالك.")

    if _get(data, "spray_blocked"):
        parts.append("Traitement pulvérisation bloqué aujourd'hui (vent fort).")

    return " ".join(parts)


def template_texts(payload: dict[str, Any]) -> dict[str, str]:
    """Offline fallback — numbers only from payload, never invented."""
    return {
        "fr": _fr(payload),
        "ar": _ar(payload),
        "darija": _darija(payload),
    }


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
    """Answer a farmer question from the last recommendation + FAO/INRA folder.

    The answer is built from the stored payload and the reference pages; the
    language model is only consulted when available and never invents a number.
    """
    base = await explain(last_payload)
    context = _build_ask_context(question, last_payload)
    base["answer"] = context
    base["note"] = (
        f"Ask Qatra (MVP): answered from stored recommendation + knowledge folder. "
        f"Q={question[:200]}"
    )
    return base


def _build_ask_context(question: str, payload: dict[str, Any]) -> str:
    """Ground the answer in the payload and the knowledge reference pages."""
    q = (question or "").lower()
    refs = _relevant_reference(q)
    ref_blob = "\n".join(f"- {p.name}" for p in refs) or "(no matching reference page)"

    if "irrig" in q or "eau" in q or "water" in q or "lma" in q or "سقي" in q:
        return (
            f"Besoin estimé {_get(payload, 'etc_mm')} mm (ETc), "
            f"pluie utile {_get(payload, 'effective_rain_mm', 0.0)} mm, "
            f"dose brute {_get(payload, 'gross_irrigation_mm')} mm "
            f"(method: {_get(payload, 'irrigation_method', 'n/a')}). "
            f"Reference: {ref_blob}"
        )
    if "risque" in q or "maladie" in q or "fongique" in q or "fong" in q or " disease" in q or "مرض" in q or "خاطر" in q:
        return (
            f"Risque: {_get(payload, 'fungal_risk', _get(payload, 'disease_risk', 'low'))}. "
            f"Reference: {ref_blob}"
        )
    if "vent" in q or "spray" in q or "رش" in q:
        blocked = _get(payload, "spray_blocked", False)
        return (
            f"Spray blocked={blocked} (wind {_get(payload, 'wind_kmh', 'n/a')} km/h). "
            f"Reference: {ref_blob}"
        )
    # Generic fallback: state the stored recommendation.
    return (
        f"From the last recommendation (status={_get(payload, 'status', 'needs_check')}): "
        f"ETc {_get(payload, 'etc_mm')} mm, dose {_get(payload, 'gross_irrigation_mm')} mm. "
        f"Reference: {ref_blob}"
    )


def _relevant_reference(question: str) -> list[Path]:
    """Return knowledge pages that mention a token from the question."""
    q = (question or "").lower()
    tokens = [t for t in q.split() if len(t) > 3]
    matches: list[Path] = []
    for p in list_reference_pages():
        try:
            text = p.read_text(encoding="utf-8").lower()
        except Exception:
            continue
        name = p.name.lower()
        if any(tok in text or tok in name for tok in tokens):
            matches.append(p)
    return matches