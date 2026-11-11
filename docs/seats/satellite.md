# Seat · Satellite

**Branch:** `seat/satellite`

## Owns

- `backend/app/services/satellite_service.py`
- Cloud mask, NDVI, NDWI, valid pixel %, vigor PNG
- Sentinel-1 fallback when optical is too cloudy
- Fixtures under `backend/tests/fixtures/`

## Original MVP checklist

This is retained as historical context. The current live provider is Google
Earth Engine, not a Copernicus Data Space client stub.

1. [x] Compute NDVI / Gao NDWI/NDMI for `MA-001` or return null with a reason
2. [x] If `valid_pixel_pct < 70`, try Sentinel-1 without producing optical indices
3. [x] Write observations with source, date and quality flags
4. [x] Never invent an index when imagery is missing

## Implementation notes

The reusable implementation is in `backend/app/services/satellite_service.py`.
It accepts a parcel GeoJSON polygon, validates it with Shapely, and searches
`COPERNICUS/S2_SR_HARMONIZED` in a configurable date window. SCL classes 0,
1, 2, 3, 8, 9, 10 and 11 (NoData, defective, dark/shadow, cloud, cirrus
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

## Integration function reference

All functions below are Satellite-owned and live in
`backend/app/services/satellite_service.py`.

### `fetch_indices`

```python
async def fetch_indices(
    bbox: list[float] | None = None,
    *, geojson: Mapping[str, Any] | BaseGeometry | None = None,
    analysis_date: date | str | None = None,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
    offline_dir: str | Path | None = None,
    client: SceneClient | None = None,
    radar_client: SceneClient | None = None,
    generate_overlay: bool = True,
    plot_id: str | None = None,
) -> SatelliteObservation
```

Use for the existing five-field observation path. A missing or unusable optical
observation preserves `None` for NDVI and contract `ndwi`. Sentinel-1 fallback
is marked with `satellite_source="sentinel-1"` and `quality="radar_fallback"`;
it never supplies optical indices. Invalid geometry, provider failure, stale
imagery and low coverage are represented by `reason`/`quality`; values are
never fabricated. `to_contract_dict()` returns only the existing five fields.

### `fetch_acquisitions`

```python
async def fetch_acquisitions(
    *, geojson: Mapping[str, Any] | BaseGeometry,
    start_date: date | str, end_date: date | str,
    client: TimeSeriesSceneClient | None = None,
    max_acquisitions: int | None = None,
) -> list[SatelliteAcquisition]
```

Returns sorted, de-duplicated Sentinel-2 observations with scene ID, date,
NDVI, Gao NDWI/NDMI (`ndmi`), coverage, quality and bounds. Radar fallback is
not used. Missing scenes produce `[]`; invalid dates or max counts raise
`SatelliteServiceError`. `max_acquisitions` bounds provider processing.

### `compare_acquisitions`

```python
def compare_acquisitions(
    earlier: SatelliteAcquisition,
    later: SatelliteAcquisition,
) -> SatelliteComparison
```

Returns raw NDVI/NDMI changes and minimum valid coverage. It raises
`IncompatibleSatelliteObservations` for missing IDs/dates, non-optical sources,
non-chronological scenes, geometry mismatch, missing indices, low coverage or
non-`good` quality. No agronomic threshold is applied.

### `compare_scene_maps`

```python
async def compare_scene_maps(
    *, geojson: Mapping[str, Any] | BaseGeometry,
    earlier_scene_id: str, later_scene_id: str,
    generate_overlay: bool = True,
    client: SpatialDifferenceClient | None = None,
) -> SatelliteSpatialDifference
```

Resolves Sentinel-2 `PRODUCT_ID` or `system:index` values, intersects SCL and
B4/B8/B11 masks on the later B08 10 m grid, and returns dates, coverage,
quality, bounds, formulas and optional NDVI/NDMI delta PNG paths. It raises
`IncompatibleSatelliteObservations` for missing/incompatible scenes or coverage
below 70%. Overlay download failure leaves its path `None`.

### `build_satellite_analysis_report`

```python
async def build_satellite_analysis_report(
    *, geojson: Mapping[str, Any] | BaseGeometry,
    start_date: date | str, end_date: date | str,
    earlier_scene_id: str | None = None,
    later_scene_id: str | None = None,
    include_spatial_difference: bool = False,
    generate_overlays: bool = False,
    client: TimeSeriesSceneClient | None = None,
    spatial_client: SpatialDifferenceClient | None = None,
    max_acquisitions: int | None = None,
) -> dict[str, Any]
```

Fetches acquisitions once, reuses them for temporal comparison, and invokes
spatial processing only when explicitly enabled. It returns `no_data` for an
empty acquisition set, `unavailable` for a provider error, and `partial` with
`missing_data_reasons` for incomplete selection or spatial failure. Invalid
geometry/date windows and ranges over 366 days raise before provider work.

### Historical MA-001 demonstration

Real historical demonstration captured on 2026-11-11; it is not a current-day
fixture or a promise of future availability:

```json
{
  "plot_id": "MA-001",
  "date_range": ["2026-09-01", "2026-11-11"],
  "earlier": {"scene_id": "20260902T110621_20260902T111416_T29SPT", "ndvi": 0.0749943906, "ndmi": -0.0859788342, "valid_pixel_pct": 100.0},
  "later": {"scene_id": "20261101T111211_20261101T112054_T29SPT", "ndvi": 0.0787901117, "ndmi": -0.0942158232, "valid_pixel_pct": 100.0},
  "temporal": {"ndvi_change": 0.003796, "ndmi_change": -0.008237, "quality": "compatible"},
  "spatial": {"shared_valid_pixel_pct": 100.0, "quality": "good", "bounds": [-7.5898, 33.5731, -7.5888, 33.574]},
  "limitations": ["Spectral indices are indicators, not direct crop-disease or water-stress diagnoses."]
}
```

The corresponding ignored JSON report and `ndvi_delta_*`/`ndmi_delta_*` PNGs
are stored under `backend/artifacts/satellite/`.

## Handoff risks and boundaries

- Backend still needs an adapter/API decision for the richer report; no shared
  contract change is required for initial integration.
- Overlay paths are local filesystem paths and need deployment storage/serving
  decisions before production use.
- Earth Engine requires configured `GEE_PROJECT_ID` and credentials; live tests
  are not deterministic CI tests.
- Scene selections must use the `scene_id` values returned by
  `fetch_acquisitions()`; the report does not fabricate or silently substitute
  scenes.
- Spectral indices do not diagnose disease or water stress without agronomic,
  weather and field observations.

The Satellite test suite covers masking, formulas, nulls, freshness, temporal
and spatial comparisons, report complete/partial/no-data cases, overlays and
provider graph optimizations. No additional Satellite-owned bug was identified
in this handoff review.
