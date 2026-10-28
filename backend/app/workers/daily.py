"""Daily recommendation worker — Backend seat.

Enqueue all plots into Redis, then process the queue. Safe to run from
Compose (`python -m app.workers.daily`) or via POST /api/v1/jobs/daily.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time

from app.core.database import Base, SessionLocal, engine
from app.core.geo import centroid_lon_lat, parse_plot_geom
from app.core.redis_client import enqueue_many, pop_plot, queue_length
from app.domain.models import Farmer, Message, Plot, Recommendation
from app.services import notification
from app.services.orchestrator import run_recommendation

logger = logging.getLogger("qatra.daily")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def enqueue_all_plots() -> int:
    db = SessionLocal()
    try:
        ids = [p.public_id for p in db.query(Plot).order_by(Plot.id).all()]
        return enqueue_many(ids)
    finally:
        db.close()


async def process_one(public_id: str) -> dict | None:
    db = SessionLocal()
    try:
        plot = db.query(Plot).filter(Plot.public_id == public_id).first()
        if not plot:
            logger.warning("plot missing: %s", public_id)
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
        logger.info("processed %s status=%s", public_id, payload.get("status"))
        return payload
    finally:
        db.close()


async def drain_queue(max_items: int | None = None) -> int:
    done = 0
    while True:
        if max_items is not None and done >= max_items:
            break
        public_id = pop_plot(timeout=1)
        if not public_id:
            break
        await process_one(public_id)
        done += 1
    return done


async def run_once() -> dict:
    """Enqueue every plot, then drain the queue."""
    Base.metadata.create_all(bind=engine)
    n = enqueue_all_plots()
    processed = await drain_queue()
    return {"enqueued": n, "processed": processed, "remaining": queue_length()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Qatra daily recommendation worker")
    parser.add_argument("--once", action="store_true", help="Enqueue all plots, drain, exit")
    parser.add_argument("--loop", action="store_true", help="Process queue forever")
    parser.add_argument("--sleep", type=int, default=5, help="Seconds between idle polls in --loop")
    args = parser.parse_args()

    if args.loop:
        Base.metadata.create_all(bind=engine)
        logger.info("worker loop started")
        while True:
            if queue_length() == 0:
                enqueue_all_plots()
            n = asyncio.run(drain_queue())
            if n == 0:
                time.sleep(args.sleep)
        return

    result = asyncio.run(run_once())
    print(result)


if __name__ == "__main__":
    main()
