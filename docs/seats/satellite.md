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

## Implementation notes

The reusable implementation is in `backend/app/services/satellite_service.py`.
It accepts a parcel GeoJSON polygon, validates it with Shapely, and searches
`COPERNICUS/S2_SR_HARMONIZED` in a configurable date window. SCL classes 3,
0, 1, 2, 3, 8, 9, 10 and 11 (NoData, defective, dark/shadow, cloud, cirrus
and snow/ice) are masked. Valid pixels
are counted only inside the parcel. The quality threshold is 70 percent.

NDVI is `(B08 - B04) / (B08 + B04)`. Since the service uses Gao NDWI, NDWI is
`(B08 - B11) / (B08 + B11)`. Sentinel-2 surface reflectance is explicitly
converted from its 10,000 scale before calculation. If the optical result is
not usable, Sentinel-1 is recorded only when an actual scene is found; it
never supplies NDVI or NDWI.

The current shared contract does not contain `radar_fallback`, quality details,
or an overlay path. These are therefore kept on `SatelliteObservation` and are
not emitted by `to_contract_dict()` until the team approves a contract change.

### Earth Engine configuration

Install the backend requirements, create `.env` from `.env.example`, and set
`GEE_PROJECT_ID` to the Google Cloud project used by Earth Engine. Configure
Application Default Credentials or a service-account JSON path in
`GEE_CREDENTIALS_PATH`. The backend calls `ee.Initialize(project=...)`; it
does not run interactive authentication. Docker must receive the environment
variables and mount the credentials file read-only if a file path is used.

### Offline scene manifest

Set `offline_dir` when calling `fetch_indices`. A manifest is a previously
downloaded/processed scene and must preserve its real acquisition date:

```json
{
  "type": "qatra-satellite-scene",
  "observed_at": "2025-06-01T10:20:00Z",
  "bounds": [-8, 33, -7, 34],
  "ndvi": 0.61,
  "ndwi": 0.18,
  "valid_pixel_pct": 88,
  "vigor_map_path": "artifacts/satellite/ndvi_2025-06-01.png"
}
```

An absent or incomplete manifest returns missing values; it is never treated as
a recent acquisition.

### Backend integration proposal

The existing orchestrator currently calls `fetch_indices()` without a parcel
polygon. The Backend seat should pass the plot GeoJSON and date window, then
map `observation.to_contract_dict()` to the five existing Satellite fields.
No Backend file was changed in this implementation.

## Contract fields

`ndvi`, `ndwi`, `ndvi_observed_at`, `valid_pixel_pct`, `satellite_source`
