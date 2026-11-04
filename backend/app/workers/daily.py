"""Daily recommendation worker — Backend seat.

Enqueue all plots into Redis, then process the queue. Safe to run from
Compose (`python -m app.workers.daily`) or via POST /api/v1/jobs/daily.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time

from app.core.database import SessionLocal
from app.core.geo import centroid_lon_lat, parse_plot_geom
from app.core.redis_client import DAILY_QUEUE, get_redis, enqueue_many, pop_plot, queue_length
from app.domain.models import Farmer, Message, Plot, Recommendation
from app.services import notification
from app.services.explain import save_last_stored_state
from app.services.orchestrator import run_recommendation

logger = logging.getLogger("qatra.daily")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def enqueue_all_plots(queue: str = DAILY_QUEUE, user: Farmer | None = None) -> int:
    db = SessionLocal()
    try:
        query = db.query(Plot)
        if user is not None:
            if user.role == "advisor":
                query = query.filter(Plot.advisor_id == user.id)
            else:
                query = query.filter(Plot.owner_id == user.id)
        ids = [p.public_id for p in query.order_by(Plot.id).all()]
        return enqueue_many(ids, queue=queue)
    finally:
        db.close()


async def process_one(public_id: str, user: Farmer | None = None) -> dict | None:
    db = SessionLocal()
    try:
        plot = db.query(Plot).filter(Plot.public_id == public_id).first()
        if not plot:
            logger.warning("plot missing: %s", public_id)
            return None
        if user is not None:
            allowed = plot.advisor_id == user.id if user.role == "advisor" else plot.owner_id == user.id
            if not allowed:
                return None
        farmer = db.get(Farmer, plot.owner_id)
        geojson = parse_plot_geom(plot.geom)
        center = centroid_lon_lat(geojson)
        lon = center[0] if center else None
        lat = center[1] if center else None

        previous = (
            db.query(Recommendation)
            .filter(Recommendation.plot_id == plot.id)
            .order_by(Recommendation.created_at.desc())
            .first()
        )
        previous_status = previous.status if previous else None

        payload = await run_recommendation(
            plot_id=plot.public_id,
            crop=plot.crop,
            stage=plot.stage,
            irrigation_method=plot.irrigation_method,
            area_ha=plot.area_ha,
            geojson=geojson,
            lat=lat,
            lon=lon,
        )

        if farmer and farmer.notify_opt_in and previous_status != payload.get("status"):
            text = (payload.get("texts") or {}).get("fr") or ""
            note = await notification.notify_farmer(
                channel="web",
                telegram_chat_id=farmer.telegram_chat_id,
                text=text,
            )
            payload["notification"] = note
            db.add(
                Message(
                    farmer_id=farmer.id,
                    plot_id=plot.id,
                    channel=note.get("channel", "web"),
                    direction="outbound",
                    body=text,
                    status="delivered" if note.get("delivered") else "queued",
                )
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
        save_last_stored_state(payload)
        logger.info("processed %s status=%s", public_id, payload.get("status"))
        return payload
    finally:
        db.close()


async def drain_queue(max_items: int | None = None, *, queue: str = DAILY_QUEUE, user: Farmer | None = None) -> dict:
    done = 0
    failed = []
    skipped = 0
    while True:
        if max_items is not None and done + len(failed) + skipped >= max_items:
            break
        public_id = pop_plot(timeout=1, queue=queue)
        if not public_id:
            break
        try:
            result = await process_one(public_id, user=user)
            if result is None:
                skipped += 1
            else:
                done += 1
        except Exception:
            logger.exception("daily recommendation failed: %s", public_id)
            failed.append(public_id)
    return {"processed": done, "failed": failed, "skipped": skipped}


async def run_once(user: Farmer | None = None) -> dict:
    """Run a pass scoped to the caller; CLI runs cover all plots."""
    queue = DAILY_QUEUE if user is None else f"{DAILY_QUEUE}:user:{user.id}"
    lock = get_redis().lock(f"{queue}:lock", timeout=3600, blocking=False)
    if not lock.acquire(blocking=False):
        return {"enqueued": 0, "processed": 0, "remaining": queue_length(queue), "busy": True}
    try:
        # Resume an interrupted pass before enqueueing another one.
        n = enqueue_all_plots(queue, user) if queue_length(queue) == 0 else 0
        result = await drain_queue(queue=queue, user=user)
        return {"enqueued": n, **result, "remaining": queue_length(queue)}
    finally:
        if lock.owned():
            lock.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="Qatra daily recommendation worker")
    parser.add_argument("--once", action="store_true", help="Enqueue all plots, drain, exit")
    parser.add_argument("--loop", action="store_true", help="Process queue forever")
    parser.add_argument("--sleep", type=int, default=5, help="Seconds before retrying a failed pass")
    parser.add_argument("--interval", type=int, default=86400, help="Seconds between daily passes")
    args = parser.parse_args()

    if args.loop:
        logger.info("worker loop started")
        while True:
            try:
                logger.info("daily pass: %s", asyncio.run(run_once()))
                time.sleep(max(1, args.interval))
            except Exception:
                logger.exception("daily pass failed; retrying")
                time.sleep(max(1, args.sleep))
        return

    result = asyncio.run(run_once())
    print(result)


if __name__ == "__main__":
    main()
