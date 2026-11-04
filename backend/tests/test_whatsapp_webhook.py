import hashlib
import hmac
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import whatsapp


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(whatsapp.router, prefix="/whatsapp")
    return TestClient(app)


def test_whatsapp_webhook_verification(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "whatsapp_verify_token", "verify-me")

    response = _client().get(
        "/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-me",
            "hub.challenge": "challenge-123",
        },
    )

    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_whatsapp_text_message_routes_to_ask_qatra(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "whatsapp_app_secret", "app-secret")
    called = []

    async def fake_ask_qatra(question, payload):
        called.append((question, payload))
        return {"answer": "Use the latest plot recommendation."}

    monkeypatch.setattr(whatsapp, "ask_qatra", fake_ask_qatra)
    body = json.dumps(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.1",
                                        "from": "212600000000",
                                        "type": "text",
                                        "text": {"body": "  Besoin irrigation ?  "},
                                    },
                                    {"id": "wamid.2", "type": "image"},
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    ).encode()
    signature = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()

    response = _client().post(
        "/whatsapp/webhook",
        content=body,
        headers={"content-type": "application/json", "x-hub-signature-256": signature},
    )

    assert response.status_code == 200
    assert called == [("Besoin irrigation ?", {"status": "needs_check", "plot_id": "unknown"})]
    assert response.json()["results"] == [
        {
            "message_id": "wamid.1",
            "from": "212600000000",
            "answer": {"answer": "Use the latest plot recommendation."},
        }
    ]


def test_whatsapp_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(whatsapp.settings, "whatsapp_app_secret", "app-secret")

    response = _client().post(
        "/whatsapp/webhook",
        json={"entry": []},
        headers={"x-hub-signature-256": "sha256=invalid"},
    )

    assert response.status_code == 403