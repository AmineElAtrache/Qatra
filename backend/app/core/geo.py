"""Geometry helpers for plot polygons (GeoJSON text, works without PostGIS)."""

from __future__ import annotations

import json
import re
from typing import Any


def coordinates_to_geojson(coordinates: list[list[list[float]]]) -> dict[str, Any]:
    """Build a GeoJSON Polygon Feature from ring coordinates [[[lon, lat], ...]]."""
    ring = coordinates[0]
    if ring[0] != ring[-1]:
        ring = [*ring, ring[0]]
        coordinates = [ring]
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Polygon", "coordinates": coordinates},
    }


def geojson_to_text(geojson: dict[str, Any]) -> str:
    return json.dumps(geojson, separators=(",", ":"))


def parse_plot_geom(raw: str | None) -> dict[str, Any] | None:
    """Parse stored geom (GeoJSON text or EWKT POLYGON) into a GeoJSON Feature."""
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("{"):
        data = json.loads(raw)
        if data.get("type") == "Feature":
            return data
        if data.get("type") in {"Polygon", "MultiPolygon"}:
            return {"type": "Feature", "properties": {}, "geometry": data}
        if "geometry" in data:
            return data
        return None
    # EWKT: SRID=4326;POLYGON((lon lat, ...))
    m = re.match(
        r"(?:SRID=\d+;)?POLYGON\s*\(\((.+)\)\)",
        raw,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    pts: list[list[float]] = []
    for part in m.group(1).split(","):
        nums = part.strip().split()
        if len(nums) >= 2:
            pts.append([float(nums[0]), float(nums[1])])
    if len(pts) < 3:
        return None
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return coordinates_to_geojson([pts])


def centroid_lon_lat(geojson: dict[str, Any] | None) -> tuple[float, float] | None:
    """Simple average centroid of the outer ring (good enough for Open-Meteo)."""
    if not geojson:
        return None
    geom = geojson.get("geometry", geojson)
    coords = geom.get("coordinates")
    if not coords:
        return None
    ring = coords[0] if geom.get("type") == "Polygon" else coords[0][0]
    if not ring:
        return None
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return (sum(lons) / len(lons), sum(lats) / len(lats))


def default_ma001_geojson() -> dict[str, Any]:
    return coordinates_to_geojson(
        [
            [
                [-7.5898, 33.5731],
                [-7.5888, 33.5731],
                [-7.5888, 33.5740],
                [-7.5898, 33.5740],
                [-7.5898, 33.5731],
            ]
        ]
    )
