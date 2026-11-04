"""Interface seat — in-app notifications (free, no WhatsApp Cloud API).

Outbound messages are already logged in ``messages`` by the recommendation
route and the daily worker. This router lets the signed-in user read them
and send one test notification (Friday proof: one message leaves the system).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.database import get_db
from app.domain.models import Farmer, Message, Plot
from app.services import notification

router = APIRouter()

LIST_LIMIT = 30
TEST_TEXT = "Test Qatra : les notifications fonctionnent. Vous recevrez ici la recommandation quand elle change."


def _out(m: Message, plot_ids: dict[int, str]) -> dict:
    return {
        "id": m.id,
        "plot_id": plot_ids.get(m.plot_id) if m.plot_id else None,
        "channel": m.channel,
        "direction": m.direction,
        "body": m.body,
        "status": m.status,
        "created_at": m.created_at,
    }


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    user: Farmer = Depends(get_current_farmer),
) -> list[dict]:
    rows = (
        db.query(Message)
        .filter(Message.farmer_id == user.id, Message.direction == "outbound")
        .order_by(Message.id.desc())
        .limit(LIST_LIMIT)
        .all()
    )
    plot_ids = {p.id: p.public_id for p in db.query(Plot).filter(Plot.id.in_({m.plot_id for m in rows if m.plot_id})).all()}
    return [_out(m, plot_ids) for m in rows]


@router.post("/test")
async def send_test_notification(
    db: Session = Depends(get_db),
    user: Farmer = Depends(get_current_farmer),
) -> dict:
    note = await notification.notify_farmer(
        channel=None,
        telegram_chat_id=user.telegram_chat_id,
        text=TEST_TEXT,
    )
    row = Message(
        farmer_id=user.id,
        plot_id=None,
        channel=note.get("channel", "web"),
        direction="outbound",
        body=TEST_TEXT,
        status="delivered" if note.get("delivered") else "queued",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row, {})
