"""WhatsApp Cloud API webhook routed to Ask Qatra."""

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.services.explain import ask_qatra

router = APIRouter()


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> str:
    if (
        hub_mode != "subscribe"
        or not settings.whatsapp_verify_token
        or hub_verify_token != settings.whatsapp_verify_token
        or hub_challenge is None
    ):
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return hub_challenge


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> dict[str, Any]:
    if not settings.whatsapp_app_secret or not x_hub_signature_256:
        raise HTTPException(status_code=403, detail="Webhook signature required")

    raw_body = await request.body()
    expected_signature = "sha256=" + hmac.new(
        settings.whatsapp_app_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(x_hub_signature_256, expected_signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    results = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                question = (message.get("text") or {}).get("body", "").strip()
                if not question:
                    continue
                answer = await ask_qatra(
                    question,
                    {"status": "needs_check", "plot_id": "unknown"},
                )
                results.append(
                    {
                        "message_id": message.get("id"),
                        "from": message.get("from"),
                        "answer": answer,
                    }
                )

    return {"ok": True, "results": results}