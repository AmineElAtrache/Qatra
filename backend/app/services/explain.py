"""Deterministic, multilingual Ask Qatra answers grounded in stored state and references."""

from __future__ import annotations

import json
import math
import re
import tempfile
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

_NO_DATA = {
    "en": "The latest recommendation needs verification. No irrigation amount is available yet.",
    "fr": "La dernière recommandation doit être vérifiée. Aucune dose d'irrigation n'est disponible.",
    "ar": "يجب التحقق من آخر توصية. لا توجد جرعة ري متاحة حاليا.",
    "darija": "Khass n2akdo mn akher tawsiya. Ma kaynach doza dyal s9i daba.",
}


def knowledge_dir() -> Path:
    """Resolve the knowledge folder relative to the backend package."""
    root = Path(settings.knowledge_dir)
    return root if root.is_absolute() else Path(__file__).resolve().parents[2] / root


def list_reference_pages() -> list[Path]:
    """Return all static FAO and INRA markdown reference pages."""
    root = knowledge_dir()
    if not root.is_dir():
        return []
    return sorted(page for page in root.rglob("*.md") if page.is_file())


def load_reference() -> str:
    """Concatenate all static reference pages."""
    return "\n\n---\n\n".join(
        page.read_text(encoding="utf-8") for page in list_reference_pages()
    )


def last_stored_state_path() -> Path:
    """Resolve the local JSON state path."""
    path = Path(settings.last_stored_state_path)
    return path if path.is_absolute() else Path(__file__).resolve().parents[2] / path


def load_last_stored_state() -> dict[str, Any]:
    """Load the last recommendation snapshot, failing explicitly on invalid JSON."""
    path = last_stored_state_path()
    if not path.exists():
        return {"status": "needs_check"}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read stored Ask Qatra state at {path}") from exc
    if not isinstance(state, dict):
        raise ValueError(f"Stored Ask Qatra state at {path} must be a JSON object")
    return state


def save_last_stored_state(state: dict[str, Any]) -> None:
    """Atomically persist the latest recommendation for offline channel webhooks."""
    path = last_stored_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        serialized_state = json.dumps(state, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unable to serialize Ask Qatra state for {path}") from exc
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as state_file:
            state_file.write(serialized_state + "\n")
            temporary_path = Path(state_file.name)
        temporary_path.replace(path)
    except OSError as exc:
        raise ValueError(f"Unable to save Ask Qatra state at {path}") from exc


def _stored_irrigation(data: dict[str, Any]) -> dict[str, Any]:
    irrigation = data.get("irrigation_recommendation")
    return irrigation if isinstance(irrigation, dict) else {}


def _get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return default


def _valid_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _number(data: dict[str, Any], *keys: str) -> str | None:
    value = _get(data, *keys)
    return str(value) if _valid_number(value) else None


def _status(data: dict[str, Any]) -> str:
    return str(_get(data, "status", default="needs_check")).lower()


def _show_dose(data: dict[str, Any]) -> bool:
    irrigation = _stored_irrigation(data)
    return (
        _status(data) == "show_dose"
        and (
            _valid_number(_get(data, "display_dose"))
            or _valid_number(_get(data, "gross_irrigation_mm"))
            or _valid_number(_get(data, "water_volume_mm"))
        )
    ) or (
        str(irrigation.get("action", "")).upper() == "IRRIGATE"
        and _valid_number(irrigation.get("water_volume_mm"))
    )


def _risk(data: dict[str, Any]) -> str | None:
    risk = _get(data, "fungal_risk", "disease_risk")
    if isinstance(risk, dict):
        risk = _get(risk, "level")
    if risk is None:
        return None
    return str(risk).lower()


def _metric_parts(data: dict[str, Any], language: str) -> list[str]:
    labels = {
        "en": (
            ("etc_mm", "ETc"),
            ("effective_rain_mm", "effective rain"),
            ("gross_irrigation_mm", "gross irrigation"),
        ),
        "fr": (
            ("etc_mm", "ETc"),
            ("effective_rain_mm", "pluie utile"),
            ("gross_irrigation_mm", "dose brute"),
        ),
        "ar": (
            ("etc_mm", "ETc"),
            ("effective_rain_mm", "مطر نافع"),
            ("gross_irrigation_mm", "جرعة الري الإجمالية"),
        ),
        "darija": (
            ("etc_mm", "ETc"),
            ("effective_rain_mm", "shta nafi3a"),
            ("gross_irrigation_mm", "doza dyal s9i"),
        ),
    }[language]
    parts = []
    for key, label in labels:
        value = _number(data, key)
        if key == "gross_irrigation_mm" and value is None:
            value = _number(data, "water_volume_mm")
            if value is None:
                irrigation = _stored_irrigation(data)
                nested_value = irrigation.get("water_volume_mm")
                if _valid_number(nested_value):
                    value = str(nested_value)
            if value is None:
                value = _number(data, "display_dose")
        if value is not None:
            parts.append(f"{label}: {value} mm")
    return parts


def _template(data: dict[str, Any], language: str) -> str:
    parts = []
    if _show_dose(data):
        metrics = _metric_parts(data, language)
        method = _get(data, "irrigation_method")
        if language == "en":
            text = "Stored irrigation values: " + "; ".join(metrics) + "."
            if method:
                text += f" Method: {method}."
        elif language == "fr":
            text = "Valeurs d'irrigation enregistrées : " + "; ".join(metrics) + "."
            if method:
                text += f" Méthode : {method}."
        elif language == "ar":
            text = "قيم الري المسجلة: " + "؛ ".join(metrics) + "."
            if method:
                text += f" الطريقة: {method}."
        else:
            text = "L9iyam dyal s9i li tsjlo: " + "; ".join(metrics) + "."
            if method:
                text += f" Tari9a: {method}."
        parts.append(text)
    elif not _risk(data) and _get(data, "spray_blocked") is None:
        return _NO_DATA[language]
    else:
        parts.append(_NO_DATA[language])

    risk = _risk(data)
    if risk:
        risk_messages = {
            "high": {
                "en": "Fungal risk is high; monitor the crop.",
                "fr": "Le risque fongique est élevé ; surveillez la culture.",
                "ar": "خطر الأمراض الفطرية مرتفع؛ راقب المحصول.",
                "darija": "Kayn khatar kbir dyal lfetriyat; ra9eb lma7soul.",
            },
            "medium": {
                "en": "Fungal risk is moderate; monitoring is advised.",
                "fr": "Le risque fongique est modéré ; une surveillance est conseillée.",
                "ar": "خطر الأمراض الفطرية متوسط؛ يُنصح بالمراقبة.",
                "darija": "Kayn khatar motawasset dyal lfetriyat; ra9eb lma7soul.",
            },
        }
        if risk in risk_messages:
            parts.append(risk_messages[risk][language])
    if _get(data, "spray_blocked") is True:
        spray = {
            "en": "Spraying is blocked according to the stored recommendation.",
            "fr": "La pulvérisation est bloquée selon la recommandation enregistrée.",
            "ar": "الرش ممنوع حسب التوصية المسجلة.",
            "darija": "Rach mamnou3 7sab tawsiya li tsjlat.",
        }
        parts.append(spray[language])
    elif _get(data, "spray_blocked") is False:
        spray = {
            "en": "The stored recommendation does not block spraying.",
            "fr": "La recommandation enregistrée ne bloque pas la pulvérisation.",
            "ar": "التوصية المسجلة لا تمنع الرش.",
            "darija": "Tawsiya li tsjlat ma katmna3ch rach.",
        }
        parts.append(spray[language])
    return " ".join(parts)


def template_texts(payload: dict[str, Any]) -> dict[str, str]:
    """Build deterministic responses using only numeric values present in state."""
    return {
        "en": _template(payload, "en"),
        "fr": _template(payload, "fr"),
        "ar": _template(payload, "ar"),
        "darija": _template(payload, "darija"),
    }


async def ollama_available() -> bool:
    """Check local Ollama health; answers remain deterministic even when it is healthy."""
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


async def explain(payload: dict[str, Any]) -> dict[str, str]:
    """Return offline templates; never accept generated model content as advice."""
    await ollama_available()
    return template_texts(payload)


def _language(question: str, language: str | None = None) -> str:
    if language and language.lower().split("-")[0] in {"en", "fr", "ar"}:
        return language.lower().split("-")[0]
    if re.search(r"[\u0600-\u06ff]", question):
        return "ar"
    if re.search(r"\b(lma|s9i|sqi|doza|wach|chno)\b", question.lower()):
        return "darija"
    if re.search(
        r"\b(comment|combien|eau|irrigation|besoin|risque|maladie|vent|culture)\b|[àâçéèêëîïôùûüÿœ]",
        question.lower(),
    ):
        return "fr"
    return "en"


def _topic(question: str) -> str:
    normalized = question.lower()
    if any(
        word in normalized
        for word in ("irrig", "water", "eau", "lma", "s9i", "sqi", "سقي", "ماء", "ري")
    ):
        return "irrigation"
    if any(
        word in normalized
        for word in ("risk", "risque", "disease", "maladie", "fung", "مرض", "خطر")
    ):
        return "disease"
    if any(
        word in normalized for word in ("wind", "spray", "vent", "pulv", "رش", "ريح")
    ):
        return "spray"
    return "general"


def _reference_quotes(topic: str) -> list[tuple[str, str]]:
    keywords = {
        "irrigation": (
            "rain",
            "demand",
            "irrigation",
            "dose",
            "root zone",
            "crop coefficient",
            "etc",
        ),
        "disease": ("risk", "temperature", "humidity", "rain", "disease"),
        "spray": ("spray", "wind", "blocked"),
        "general": ("explanation", "stored", "reference"),
    }[topic]
    quotes: list[tuple[str, str]] = []
    for page in list_reference_pages():
        if topic == "irrigation" and "fao" not in page.parts:
            continue
        if topic in {"disease", "spray"} and "inra" not in page.parts:
            continue
        source = "FAO" if "fao" in page.parts else "INRA"
        paragraphs = page.read_text(encoding="utf-8").split("\n\n")
        for paragraph in paragraphs:
            if "|" in paragraph:
                continue
            text = " ".join(
                line.strip().lstrip("- ").strip() for line in paragraph.splitlines()
            ).strip()
            lowered = text.lower()
            if (
                not text
                or text.startswith("#")
                or text.startswith("|")
                or text.startswith("`")
                or text.startswith("Source:")
                or text.startswith("Reference")
                or len(text) < 40
                or any(char.isdigit() for char in text)
                or re.search(r"\bmm\b|_[a-z]+", lowered)
                or not any(word in lowered for word in keywords)
            ):
                continue
            quotes.append((source, text))
            if len(quotes) == 2:
                return quotes
    return quotes


def _localized_answer(question: str, payload: dict[str, Any], language: str) -> str:
    answer = _template(payload, language)
    quotes = _reference_quotes(_topic(question))
    if quotes:
        quote_label = {
            "en": "Reference",
            "fr": "Référence",
            "ar": "المرجع",
            "darija": "Marja3",
        }[language]
        answer += " " + " ".join(
            f"{quote_label} ({source}): “{quote}”" for source, quote in quotes
        )
    return answer


async def ask_qatra(
    question: str,
    last_payload: dict[str, Any] | None = None,
    language: str | None = None,
) -> dict[str, str]:
    """Unified Ask handler for app and messaging webhooks."""
    payload = last_payload if last_payload is not None else load_last_stored_state()
    texts = await explain(payload)
    response_language = _language(question, language)
    return {
        **texts,
        "language": response_language,
        "answer": _localized_answer(question, payload, response_language),
        "note": "Answered deterministically from the last stored state and static FAO/INRA references.",
    }
