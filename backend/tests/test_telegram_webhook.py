from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import telegram


def test_telegram_webhook_uses_unified_ask_handler(monkeypatch):
    app = FastAPI()
    app.include_router(telegram.router, prefix="/telegram")
    calls = []

    async def fake_ask_qatra(question, payload=None, language=None):
        calls.append((question, payload, language))
        return {"answer": "Stored-state response"}

    monkeypatch.setattr(telegram.settings, "telegram_webhook_secret", "")
    monkeypatch.setattr(telegram, "ask_qatra", fake_ask_qatra)
    response = TestClient(app).post(
        "/telegram/webhook",
        json={
            "message": {
                "text": "How much water?",
                "chat": {"id": 123},
                "from": {"language_code": "fr"},
            }
        },
    )

    assert response.status_code == 200
    assert calls == [("How much water?", None, "fr")]
    assert response.json()["answer"] == {"answer": "Stored-state response"}
