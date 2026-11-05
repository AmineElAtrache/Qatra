"""Agronomy seat — season totals read from stored recommendations.

The arithmetic lives in ``agronomy_service.season_totals`` (pure, tested);
this module only fetches the rows of one plot.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.domain.models import Plot, Recommendation
from app.services.agronomy_service import SeasonTotals, season_start, season_totals


def today() -> date:
    """Season day in UTC (Morocco is UTC+0/+1). Patched in tests."""
    return datetime.now(timezone.utc).date()


def plot_season(db: Session, plot: Plot, on: date | None = None) -> SeasonTotals:
    day = on or today()
    start = datetime.combine(season_start(day), datetime.min.time())
    rows = (
        db.query(Recommendation)
        .filter(Recommendation.plot_id == plot.id, Recommendation.created_at >= start)
        .order_by(Recommendation.created_at.asc(), Recommendation.id.asc())
        .all()
    )
    return season_totals(
        ((r.created_at, r.payload or {}) for r in rows if r.created_at is not None),
        today=day,
        area_ha=plot.area_ha,
    )
