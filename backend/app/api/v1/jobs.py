"""Backend job triggers — daily Redis worker."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_farmer
from app.core.redis_client import queue_length
from app.domain.models import Farmer
from app.workers.daily import run_once

router = APIRouter()


@router.post("/daily")
async def trigger_daily(farmer: Farmer = Depends(get_current_farmer)) -> dict:
    """Run one daily pass: enqueue all plots, process queue, return counts."""
    _ = farmer
    result = await run_once()
    result["queue_length"] = queue_length()
    return result


@router.get("/daily/status")
def daily_status(farmer: Farmer = Depends(get_current_farmer)) -> dict:
    _ = farmer
    return {"queue_length": queue_length()}
