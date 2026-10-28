from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.database import get_db
from app.domain.models import Farmer, Plot, Recommendation
from app.services.explain import ask_qatra

router = APIRouter()


class AskIn(BaseModel):
    question: str


@router.post("/{public_id}/ask")
async def ask(
    public_id: str,
    body: AskIn,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> dict:
    plot = db.query(Plot).filter(Plot.public_id == public_id, Plot.owner_id == farmer.id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    last = (
        db.query(Recommendation)
        .filter(Recommendation.plot_id == plot.id)
        .order_by(Recommendation.created_at.desc())
        .first()
    )
    if not last:
        raise HTTPException(status_code=400, detail="No recommendation yet")
    answer = await ask_qatra(body.question, last.payload)
    return {"answer": answer, "from_recommendation_id": last.id}
