# Seat · Satellite

**Branch:** `seat/satellite`

## Owns

- `backend/app/services/satellite_service.py`
- Cloud mask, NDVI, NDWI, valid pixel %, vigor PNG
- Sentinel-1 fallback when optical is too cloudy
- Fixtures under `backend/tests/fixtures/`

## First MVP tasks

1. [ ] Client stub for Copernicus Data Space (auth + one scene)
2. [ ] Compute NDVI / NDWI for `MA-001` bbox (or return null + reason)
3. [ ] If `valid_pixel_pct < 70`, try Sentinel-1 path (no fake NDVI)
4. [ ] Write observation with `source`, `observed_at`, quality flags
5. [ ] Never invent an index when the image is missing

## Contract fields

`ndvi`, `ndwi`, `ndvi_observed_at`, `valid_pixel_pct`, `satellite_source`
