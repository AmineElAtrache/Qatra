from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.database import get_db
from app.core.geo import coordinates_to_geojson, geojson_to_text, parse_plot_geom
from app.domain.models import Farmer, Plot

router = APIRouter()


class PlotCreate(BaseModel):
    public_id: str = Field(..., examples=["MA-001"])
    crop: str = "citrus"
    stage: str = "fruit_growth"
    irrigation_method: str = "drip"
    area_ha: float = 1.2
    last_irrigation_on: date | None = None
    coordinates: list[list[list[float]]] | None = None
    geojson: dict[str, Any] | None = None


class PlotOut(BaseModel):
    id: int
    public_id: str
    crop: str
    stage: str
    irrigation_method: str
    area_ha: float
    geojson: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


def _normalize_feature(body: PlotCreate) -> dict[str, Any] | None:
    if body.geojson:
        data = body.geojson
        if data.get("type") == "Feature":
            return data
        if data.get("type") in {"Polygon", "MultiPolygon"}:
            return {"type": "Feature", "properties": {}, "geometry": data}
        if "geometry" in data:
            return data
    if body.coordinates:
        return coordinates_to_geojson(body.coordinates)
    return None


def _plot_out(plot: Plot) -> PlotOut:
    return PlotOut(
        id=plot.id,
        public_id=plot.public_id,
        crop=plot.crop,
        stage=plot.stage,
        irrigation_method=plot.irrigation_method,
        area_ha=plot.area_ha,
        geojson=parse_plot_geom(plot.geom),
    )


@router.post("", response_model=PlotOut)
def create_plot(
    body: PlotCreate,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> PlotOut:
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
    feature = _normalize_feature(body)
    if feature is not None:
        plot.geom = geojson_to_text(feature)
    db.add(plot)
    db.commit()
    db.refresh(plot)
    return _plot_out(plot)


@router.get("", response_model=list[PlotOut])
def list_plots(
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> list[PlotOut]:
    plots = db.query(Plot).filter(Plot.owner_id == farmer.id).all()
    return [_plot_out(p) for p in plots]


@router.get("/{public_id}", response_model=PlotOut)
def get_plot(
    public_id: str,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> PlotOut:
    plot = db.query(Plot).filter(Plot.public_id == public_id, Plot.owner_id == farmer.id).first()
    if not plot:
        raise HTTPException(status_code=404, detail="Plot not found")
    return _plot_out(plot)
