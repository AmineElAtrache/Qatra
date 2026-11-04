"""Backend job triggers — daily Redis worker."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_farmer
from app.core.redis_client import DAILY_QUEUE, queue_length
from app.domain.models import Farmer
from app.workers.daily import run_once

router = APIRouter()


@router.post("/daily")
async def trigger_daily(farmer: Farmer = Depends(get_current_farmer)) -> dict:
    """Run recommendations only for owned or assigned plots."""
    result = await run_once(user=farmer)
    result["queue_length"] = result["remaining"]
    return result


@router.get("/daily/status")
def daily_status(farmer: Farmer = Depends(get_current_farmer)) -> dict:
    return {"queue_length": queue_length(f"{DAILY_QUEUE}:user:{farmer.id}")}
