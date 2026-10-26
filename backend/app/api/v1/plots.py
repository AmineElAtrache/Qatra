from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.database import get_db
from app.domain.models import Farmer, Plot

router = APIRouter()


class PlotCreate(BaseModel):
    public_id: str = Field(..., examples=["MA-001"])
    crop: str = "citrus"
    stage: str = "fruit_growth"
    irrigation_method: str = "drip"
    area_ha: float = 1.2
    last_irrigation_on: date | None = None
    # GeoJSON polygon coordinates [[[lon, lat], ...]]
    coordinates: list[list[list[float]]] | None = None


class PlotOut(BaseModel):
    id: int
    public_id: str
    crop: str
    stage: str
    irrigation_method: str
    area_ha: float

    model_config = {"from_attributes": True}


@router.post("", response_model=PlotOut)
def create_plot(
    body: PlotCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> Plot:
    if db.query(Plot).filter(Plot.public_id == body.public_id).first():
        raise HTTPException(status_code=400, detail="public_id already exists")
    plot = Plot(
        public_id=body.public_id,
        owner_id=farmer.id,
        crop=body.crop,
        stage=body.stage,
        irrigation_method=body.irrigation_method,
        area_ha=body.area_ha,
        last_irrigation_on=body.last_irrigation_on,
    )
    if body.coordinates:
        # WKT polygon — PostGIS; Backend seat can refine with GeoAlchemy helpers
        ring = body.coordinates[0]
        coords = ", ".join(f"{lon} {lat}" for lon, lat in ring)
        plot.geom = f"SRID=4326;POLYGON(({coords}))"
    db.add(plot)
    db.commit()
    db.refresh(plot)
    return plot


@router.get("", response_model=list[PlotOut])
def list_plots(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> list[Plot]:
    return db.query(Plot).filter(Plot.owner_id == farmer.id).all()
