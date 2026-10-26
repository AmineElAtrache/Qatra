"""Interface seat — web notification or Telegram. No WhatsApp Cloud API for MVP."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


async def notify_farmer(
    *,
    channel: str | None,
    telegram_chat_id: str | None,
    text: str,
    audio_path: str | None = None,
) -> dict[str, Any]:
    ch = channel or settings.notification_channel
    if ch == "telegram" and settings.telegram_bot_token and telegram_chat_id:
        return await _telegram_send(telegram_chat_id, text)
    # Default: in-app / web — caller stores message; nothing billed.
    return {"channel": "web", "delivered": False, "queued": True, "text": text, "audio": audio_path}


async def _telegram_send(chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": text})
            return {"channel": "telegram", "delivered": r.status_code == 200, "status_code": r.status_code}
    except Exception as exc:
        return {"channel": "telegram", "delivered": False, "error": str(exc)}
