import json
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.core.database import get_db
from app.core.config import settings
from app.core.geo import coordinates_to_geojson, geojson_to_text, parse_plot_geom
from app.domain.models import Farmer, Plot, Recommendation
from app.services.satellite_service import InvalidGeoJSON, find_overlay_path, validate_polygon

router = APIRouter()


class AdvisorAssignment(BaseModel):
    advisor_id: int | None = None


@router.put("/{public_id}/advisor")
def assign_advisor(
    public_id: str,
    body: AdvisorAssignment,
    db: Session = Depends(get_db),
    farmer: Farmer = Depends(get_current_farmer),
) -> dict:
    plot = db.query(Plot).filter(Plot.public_id == public_id, Plot.owner_id == farmer.id).first()
    if plot is None:
        raise HTTPException(status_code=404, detail="Plot not found")
    if body.advisor_id is not None:
        advisor = db.get(Farmer, body.advisor_id)
        if advisor is None or advisor.role != "advisor":
            raise HTTPException(status_code=422, detail="A valid advisor is required")
    plot.advisor_id = body.advisor_id
    db.commit()
    return {"public_id": plot.public_id, "advisor_id": plot.advisor_id}


class PlotCreate(BaseModel):
    public_id: str = Field(..., min_length=1, max_length=64, examples=["MA-001"])
    crop: str = "citrus"
    stage: str = "fruit_growth"
    irrigation_method: str = "drip"
    area_ha: float = Field(default=1.2, gt=0, allow_inf_nan=False)
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


@router.get("/{public_id}/satellite-overlay")
def get_satellite_overlay(
    public_id: str,
    db: Session = Depends(get_db),
    user: Farmer = Depends(get_current_farmer),
) -> FileResponse:
    """Serve the latest authorized real satellite overlay as a PNG."""
    query = db.query(Plot).filter(Plot.public_id == public_id)
    if user.role == "advisor":
        query = query.filter(Plot.advisor_id == user.id)
    else:
        query = query.filter(Plot.owner_id == user.id)
    plot = query.first()
    if plot is None:
        raise HTTPException(status_code=404, detail="Plot not found")

    latest = (
        db.query(Recommendation)
        .filter(Recommendation.plot_id == plot.id)
        .order_by(Recommendation.created_at.desc())
        .first()
    )
    payload = latest.payload if latest is not None and isinstance(latest.payload, dict) else {}
    observed = payload.get("ndvi_observed_at")
    if not observed or payload.get("satellite_source") != "sentinel-2":
        raise HTTPException(status_code=404, detail="Satellite overlay not available")

    geojson = parse_plot_geom(plot.geom)
    try:
        geometry = validate_polygon(geojson) if geojson else None
    except InvalidGeoJSON as exc:
        raise HTTPException(status_code=404, detail="Plot geometry unavailable") from exc
    if geometry is None:
        raise HTTPException(status_code=404, detail="Plot geometry unavailable")

    overlay = find_overlay_path(
        plot_id=plot.public_id,
        geometry=geometry,
        observed=str(observed)[:10],
        directory=settings.satellite_overlay_dir,
    )
    if overlay is None:
        raise HTTPException(status_code=404, detail="Satellite overlay not available")

    bounds = [float(value) for value in geometry.bounds]
    return FileResponse(
        overlay,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "X-Qatra-Overlay-Bounds": json.dumps(bounds, separators=(",", ":")),
            "X-Qatra-Overlay-Observed-At": str(observed)[:10],
        },
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
    try:
        feature = _normalize_feature(body)
        if feature is None:
            raise ValueError("Plot polygon is required")
        validate_polygon(feature)
    except (InvalidGeoJSON, ValueError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="A valid plot polygon is required") from exc
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
