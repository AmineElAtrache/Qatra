from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.database import get_db
from app.domain.models import Farmer, Plot, Recommendation
from app.services.orchestrator import run_recommendation

router = APIRouter()


@router.post("/{public_id}/recommendation")
async def create_recommendation(
    public_id: str,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> dict:
    plot = db.query(Plot).filter(Plot.public_id == public_id, Plot.owner_id == farmer.id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")

    payload = await run_recommendation(
        plot_id=plot.public_id,
        crop=plot.crop,
        stage=plot.stage,
        irrigation_method=plot.irrigation_method,
        area_ha=plot.area_ha,
    )
    row = Recommendation(
        plot_id=plot.id,
        engine_version=payload["engine_version"],
        status=payload["status"],
        etc_mm=payload.get("etc_mm"),
        gross_irrigation_mm=payload.get("gross_irrigation_mm"),
        payload=payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "recommendation": payload}


@router.get("/{public_id}/recommendations")
def list_recommendations(
    public_id: str,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> list[dict]:
    plot = db.query(Plot).filter(Plot.public_id == public_id, Plot.owner_id == farmer.id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    rows = (
        db.query(Recommendation)
        .filter(Recommendation.plot_id == plot.id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )
    return [{"id": r.id, "status": r.status, "created_at": r.created_at, "payload": r.payload} for r in rows]
