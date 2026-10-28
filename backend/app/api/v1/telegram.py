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
    chat_id = chat.get("id")
    # MVP: answer from empty payload until chat↔plot linking exists
    answer = await ask_qatra(text, {"status": "needs_check", "plot_id": "unknown"})
    return {"ok": True, "chat_id": chat_id, "answer": answer}
