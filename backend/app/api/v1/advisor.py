from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_advisor
from app.core.database import get_db
from app.domain.models import Farmer, Plot, Recommendation

router = APIRouter()


@router.get("/plots")
def advisor_plots(
    db: Session = Depends(get_db),
    advisor: Farmer = Depends(require_advisor),
) -> list[dict]:
    _ = advisor
    # MVP: advisor sees all plots (link table comes later)
    plots = db.query(Plot).all()
    out: list[dict] = []
    for p in plots:
        last = (
            db.query(Recommendation)
            .filter(Recommendation.plot_id == p.id)
            .order_by(Recommendation.created_at.desc())
            .first()
        )
        out.append(
            {
                "public_id": p.public_id,
                "stage": p.stage,
                "status": last.status if last else None,
                "etc_mm": last.etc_mm if last else None,
                "gross_irrigation_mm": last.gross_irrigation_mm if last else None,
            }
        )
    return out
