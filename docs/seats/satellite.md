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

## Temporal monitoring seam

`backend/app/services/satellite_service.py` also exposes the Satellite-owned
optical time-series seam without changing the shared contract:

- `fetch_acquisitions(geojson, start_date, end_date, max_acquisitions=None)` returns sorted,
  de-duplicated `SatelliteAcquisition` values with `scene_id`, acquisition
  date, `ndvi`, explicit `ndmi` (the same Gao formula retained as contract
  `ndwi`), valid-pixel percentage, quality, bounds, and provider metadata.
  `max_acquisitions` is applied after chronological sorting and before
  server-side reduction for Earth Engine; it therefore bounds provider work
  deterministically. A missing value means all scenes in the requested date
  range are processed.
- `compare_acquisitions(earlier, later)` returns raw `ndvi_change`,
  `ndmi_change`, and minimum shared valid coverage only for compatible,
  chronological, same-geometry Sentinel-2 observations with `good` quality
  and at least 70% valid pixels. It applies no agronomic thresholds.

Backend can later persist these observations or expose a plot-scoped history
endpoint. Interface can use the returned dates and scene IDs for date
selection and render separate NDVI/NDMI layers. Sentinel-1 is intentionally
not part of this time-series path because it cannot provide optical indices.

The Earth Engine implementation maps one summary feature per image on the
server, combining NDVI, NDMI, valid coverage, date, and scene ID into one
FeatureCollection response. It does not download images or issue separate
regional `getInfo()` calls for each acquisition.

`compare_scene_maps(geojson, earlier_scene_id, later_scene_id)` resolves the
verified Sentinel-2 `PRODUCT_ID` or `system:index` values, aligns both dates
to the later scene's B08 projection at 10 m, intersects both SCL/band masks,
and optionally renders `ndvi_delta` and `ndmi_delta` parcel overlays. Delta
maps use a symmetric `[-1, 1]` scale and diverging palette centered at zero.
The function rejects missing scenes, non-chronological dates, missing bands,
and any individual or shared valid coverage below the existing 70% quality
rule. Backend/Interface can later expose these paths through a reviewed
scene-selection endpoint; no contract fields are added here.

## Reusable analysis report

`build_satellite_analysis_report(geojson, start_date, end_date,
earlier_scene_id=None, later_scene_id=None,
include_spatial_difference=False, generate_overlays=False, client=None,
spatial_client=None, max_acquisitions=None)` returns a plain,
JSON-serializable dictionary for later Backend integration. It calls
`fetch_acquisitions()` once, reuses those observations for
`compare_acquisitions()`, and calls `compare_scene_maps()` only when spatial
analysis is explicitly enabled and two compatible scenes are available.

When scene IDs are omitted, the earliest and latest available acquisitions are
selected for the temporal summary. Explicit IDs must match returned `scene_id`
values. Missing observations are never replaced with estimates. The analysis
window is bounded to 366 days.

The result contains `schema_version`, `status`, plot bounds, date range,
`available_acquisitions`, `temporal_comparison`, optional
`spatial_difference` metadata and overlay paths, `missing_data_reasons`, and a
scientific `limitations` list. A typical shape is:

```json
{
  "schema_version": "satellite-analysis-v1",
  "status": "complete",
  "plot": {"bounds": [-7.5898, 33.5731, -7.5888, 33.574]},
  "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
  "available_acquisitions": [],
  "temporal_comparison": {
    "ndvi_change": 0.13,
    "ndmi_change": -0.06,
    "valid_pixel_pct": 88.0
  },
  "spatial_difference": {
    "overlay_paths": {"ndvi_delta": null, "ndmi_delta": null},
    "bounds": [-7.5898, 33.5731, -7.5888, 33.574]
  },
  "missing_data_reasons": [],
  "limitations": ["Spectral indices are indicators, not direct diagnoses."]
}
```

Backend can later call this function from an adapter and persist or expose the
report under a reviewed API. It should map only `SatelliteObservation.to_contract_dict()`
to the existing shared contract; the richer report fields remain Satellite
metadata until the team approves an interface change.
