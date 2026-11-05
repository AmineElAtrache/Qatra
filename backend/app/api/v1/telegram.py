"""Interface seat — Telegram webhook (free alternative to WhatsApp Cloud API)."""

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings
from app.services.explain import ask_qatra

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Bad secret")
    body = await request.json()
    message = (body.get("message") or {})
    text = message.get("text") or ""
    chat = (message.get("chat") or {})
    telegram_user = message.get("from") or {}
    chat_id = chat.get("id")
    language = telegram_user.get("language_code") if isinstance(telegram_user, dict) else None
    answer = await ask_qatra(text, language=language)
    return {"ok": True, "chat_id": chat_id, "answer": answer}
