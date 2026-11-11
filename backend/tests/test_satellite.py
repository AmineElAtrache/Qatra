"""Satellite seat tests; all tests are offline and use injected adapters."""

import asyncio
import inspect
import json
import struct
import zlib
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.core.config import settings
from app.services import satellite_service as sat


PLOT = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-7.5898, 33.5731], [-7.5888, 33.5731], [-7.5888, 33.5740], [-7.5898, 33.5740], [-7.5898, 33.5731]]],
    },
}
FRESH_DATE = date.today()
FRESH_OBSERVED = FRESH_DATE.isoformat()
FRESH_RADAR_OBSERVED = (FRESH_DATE - timedelta(days=1)).isoformat()


class FakeClient:
    def __init__(self, observation):
        self.observation = observation
        self.calls = []

    def observe(self, geometry, start, end):
        self.calls.append((geometry, start, end))
        return self.observation


class FakeTimeSeriesClient:
    """Deterministic stand-in for one Earth Engine collection response."""

    def __init__(self, acquisitions):
        self.acquisitions = acquisitions
        self.calls = []

    def observe_many(self, geometry, start, end):
        self.calls.append((geometry, start, end))
        return self.acquisitions


class FakeSpatialDifferenceClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def compare_scenes(self, geometry, earlier_scene_id, later_scene_id, generate_overlay):
        self.calls.append((geometry, earlier_scene_id, later_scene_id, generate_overlay))
        return self.result


def run(coro):
    return asyncio.run(coro)


def test_valid_and_invalid_geojson():
    assert sat.validate_polygon(PLOT).geom_type == "Polygon"
    result = run(sat.fetch_indices(geojson={"type": "Point", "coordinates": [0, 0]}))
    assert result.ndvi is None
    assert result.reason == "geojson_must_be_a_valid_polygon"


def test_ndvi_ndwi_use_scaled_surface_reflectance():
    ndvi, ndwi = sat.compute_indices(2000, 6000, 3000)
    assert ndvi == 0.5
    assert ndwi == 0.333333
    assert sat.compute_indices(2000, 6000, None) == (None, None)


def test_combined_mask_requires_scl_and_all_index_bands():
    mask = sat.combined_valid_pixel_mask(
        [4, 3, 5, None],
        {
            "B4": [True, True, True, True],
            "B8": [True, True, False, True],
            "B11": [True, True, True, True],
        },
    )
    assert mask == [True, False, False, False]


def test_missing_required_band_is_diagnostic():
    missing = sat.missing_required_bands(("B4", "B8", "SCL"))
    assert missing == ("B11",)
    try:
        sat.combined_valid_pixel_mask([4], {"B4": [True], "B8": [True]})
    except sat.SatelliteServiceError as exc:
        assert str(exc) == "missing_required_bands:B11"
    else:
        raise AssertionError("missing required band was not rejected")


def test_spatial_metadata_indexes_product_and_system_ids_and_preserves_bands():
    features = [
        {
            "properties": {
                "scene_id": "system-earlier",
                "product_id": "product-earlier",
                "observed_ms": 1,
                "band_names": ["B4", "B8", "B11", "SCL"],
            }
        },
        {
            "properties": {
                "scene_id": "system-later",
                "product_id": "product-later",
                "observed_ms": 2,
                "band_names": ["B4", "B8", "SCL"],
            }
        },
    ]
    metadata = sat._parse_spatial_scene_metadata(features)
    assert metadata["product-earlier"]["band_names"] == ["B4", "B8", "B11", "SCL"]
    assert metadata["system-later"]["observed_ms"] == 2
    assert sat.missing_required_bands(metadata["product-later"]["band_names"]) == ("B11",)


def test_spatial_scene_filter_avoids_or_for_homogeneous_identifiers():
    class FakeFilter:
        @staticmethod
        def inList(field, values):
            return ("inList", field, tuple(values))

        @staticmethod
        def Or(*filters):
            return ("Or", filters)

    class FakeEE:
        Filter = FakeFilter

    products = sat._spatial_scene_filter(FakeEE, ("S2C_MSIL2A_a", "S2C_MSIL2A_b"))
    systems = sat._spatial_scene_filter(FakeEE, ("system-a", "system-b"))
    mixed = sat._spatial_scene_filter(FakeEE, ("S2C_MSIL2A_a", "system-b"))
    assert products[1] == "PRODUCT_ID"
    assert systems[1] == "system:index"
    assert mixed[0] == "Or"


def test_valid_pixel_percentage_and_scl_quality_threshold():
    assert sat.is_valid_scl(4) is True
    assert sat.is_valid_scl(3) is False
    assert sat.is_valid_scl(9) is False
    assert sat.valid_pixel_percentage(70, 100) == 70.0
    assert sat.valid_pixel_percentage(69, 100) == 69.0
    client = FakeClient(sat.SatelliteObservation(0.5, 0.2, FRESH_OBSERVED, 69, "sentinel-2", "low_valid_pixels"))
    result = run(sat.fetch_indices(geojson=PLOT, client=client, analysis_date=FRESH_DATE))
    assert result.ndvi is None
    assert result.ndwi is None
    assert result.radar_fallback is False
    assert result.valid_pixel_pct == 69
    assert result.quality == "low_valid_pixels"


def test_exactly_70_percent_keeps_optical_indices_without_radar_call():
    client = FakeClient(sat.SatelliteObservation(0.5, 0.2, FRESH_OBSERVED, 70, "sentinel-2", "good"))
    radar_client = FakeClient(sat.SatelliteObservation(None, None, FRESH_RADAR_OBSERVED, None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=client, radar_client=radar_client, analysis_date=FRESH_DATE))
    assert result.ndvi == 0.5
    assert result.radar_fallback is False
    assert radar_client.calls == []


def test_85_percent_valid_optical_indices_skip_radar():
    optical = FakeClient(sat.SatelliteObservation(0.5, 0.2, FRESH_OBSERVED, 85, "sentinel-2", "good"))
    radar = FakeClient(sat.SatelliteObservation(None, None, FRESH_RADAR_OBSERVED, None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=optical, radar_client=radar, analysis_date=FRESH_DATE))
    assert result.satellite_source == "sentinel-2"
    assert result.ndvi == 0.5
    assert radar.calls == []


def test_45_percent_valid_pixels_uses_real_sentinel1_without_optical_percentage():
    optical = FakeClient(sat.SatelliteObservation(0.5, 0.2, FRESH_OBSERVED, 45, "sentinel-2", "low_valid_pixels"))
    radar = FakeClient(sat.SatelliteObservation(None, None, FRESH_RADAR_OBSERVED, None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=optical, radar_client=radar, analysis_date=FRESH_DATE))
    assert result.satellite_source == "sentinel-1"
    assert result.radar_fallback is True
    assert result.ndvi is None and result.ndwi is None
    assert result.ndvi_observed_at == FRESH_RADAR_OBSERVED
    assert result.valid_pixel_pct is None
    assert result.reason == "optical_low_valid_pixels"
    assert result.quality_details["optical_valid_pixel_pct"] == 45


def test_null_ndvi_at_85_percent_attempts_sentinel1():
    optical = FakeClient(sat.SatelliteObservation(None, 0.2, FRESH_OBSERVED, 85, "sentinel-2", "good"))
    radar = FakeClient(sat.SatelliteObservation(None, None, FRESH_RADAR_OBSERVED, None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=optical, radar_client=radar, analysis_date=FRESH_DATE))
    assert result.satellite_source == "sentinel-1"
    assert result.reason == "optical_indices_incomplete"
    assert radar.calls


def test_null_ndwi_at_85_percent_attempts_sentinel1():
    optical = FakeClient(sat.SatelliteObservation(0.5, None, FRESH_OBSERVED, 85, "sentinel-2", "good"))
    radar = FakeClient(sat.SatelliteObservation(None, None, FRESH_RADAR_OBSERVED, None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=optical, radar_client=radar, analysis_date=FRESH_DATE))
    assert result.satellite_source == "sentinel-1"
    assert result.ndvi is None and result.ndwi is None
    assert result.reason == "optical_indices_incomplete"


def test_missing_optical_scene_attempts_sentinel1_and_preserves_nulls():
    optical = FakeClient(sat.missing_optical("no_sentinel2_scene"))
    radar = FakeClient(sat.SatelliteObservation(None, None, FRESH_RADAR_OBSERVED, None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=optical, radar_client=radar))
    assert result.satellite_source == "sentinel-1"
    assert result.ndvi is None and result.ndwi is None
    assert result.ndvi_observed_at == FRESH_RADAR_OBSERVED
    assert result.reason == "no_sentinel2_scene"


def test_missing_optical_quality_attempts_sentinel1():
    optical = FakeClient(sat.SatelliteObservation(0.5, 0.2, FRESH_OBSERVED, 85, "sentinel-2", ""))
    radar = FakeClient(sat.SatelliteObservation(None, None, FRESH_RADAR_OBSERVED, None, "sentinel-1", "radar_fallback"))
    result = run(sat.fetch_indices(geojson=PLOT, client=optical, radar_client=radar, analysis_date=FRESH_DATE))
    assert result.satellite_source == "sentinel-1"
    assert result.reason == "optical_quality_missing"


def test_no_sentinel1_scene_keeps_null_optical_values():
    optical = FakeClient(sat.SatelliteObservation(None, None, FRESH_OBSERVED, 85, "sentinel-2", "good"))
    result = run(sat.fetch_indices(geojson=PLOT, client=optical, analysis_date=FRESH_DATE))
    assert result.satellite_source == "sentinel-2"
    assert result.ndvi is None and result.ndwi is None
    assert result.reason == "no_sentinel1_scene"


def test_sentinel1_is_used_only_when_a_scene_exists(monkeypatch):
    optical = sat.SatelliteObservation(None, None, None, 20, "sentinel-2", "low_valid_pixels")
    radar = sat.SatelliteObservation(None, None, "2026-10-19", None, "sentinel-1", "radar_fallback")
    assert sat.maybe_sentinel1_fallback(optical, radar).radar_fallback is True
    assert sat.maybe_sentinel1_fallback(optical).satellite_source == "sentinel-2"
    result = run(sat.fetch_indices(geojson=PLOT, client=FakeClient(optical), radar_client=FakeClient(radar)))
    assert result.radar_fallback is True
    assert result.satellite_source == "sentinel-1"
    assert result.ndvi is None
    monkeypatch.setattr(sat, "_observe_sentinel1", lambda *args: None)
    result = run(sat.fetch_indices(geojson=PLOT, client=FakeClient(optical)))
    assert result.radar_fallback is False
    assert result.ndvi is None
    assert result.reason == "no_sentinel1_scene"


def test_offline_scene_preserves_real_date_and_contract_fields():
    fixture_dir = Path(__file__).parent / "fixtures"
    result = run(sat.fetch_indices(geojson=PLOT, offline_dir=fixture_dir, analysis_date=date(2025, 6, 10)))
    assert result.ndvi_observed_at == "2025-06-01"
    assert result.quality == "offline"
    assert result.to_contract_dict() == {
        "ndvi": 0.61,
        "ndwi": 0.18,
        "ndvi_observed_at": "2025-06-01",
        "valid_pixel_pct": 88.0,
        "satellite_source": "sentinel-2",
    }


def test_stale_live_observation_is_rejected_without_values():
    stale = FakeClient(sat.SatelliteObservation(0.7, 0.2, "2020-01-01", 95, "sentinel-2", "good"))
    result = run(sat.fetch_indices(geojson=PLOT, client=stale, analysis_date=date(2026, 1, 11)))
    assert result.ndvi is None and result.ndwi is None
    assert result.satellite_source is None
    assert result.reason == "stale_observation"
    assert result.quality_details["freshness"] == "stale"


def test_ten_day_old_live_observation_is_still_fresh():
    observed = date(2026, 1, 1)
    client = FakeClient(sat.SatelliteObservation(0.7, 0.2, observed.isoformat(), 95, "sentinel-2", "good"))
    result = run(sat.fetch_indices(geojson=PLOT, client=client, analysis_date=observed + timedelta(days=10)))
    assert result.ndvi == 0.7
    assert result.quality_details["freshness"] == "fresh"


def test_stale_offline_scene_is_rejected_without_values():
    fixture_dir = Path(__file__).parent / "fixtures"
    result = run(sat.fetch_indices(geojson=PLOT, offline_dir=fixture_dir, analysis_date=date(2026, 1, 11)))
    assert result.ndvi is None and result.ndwi is None
    assert result.reason == "stale_offline_scene"
    assert result.quality_details["stale_observed_at"] == ["2025-06-01"]


def test_earth_engine_failure_is_controlled(monkeypatch):
    def fail(*args):
        raise sat.EarthEngineUnavailable("auth_failed")

    monkeypatch.setattr(sat, "_observe_earth_engine", fail)
    monkeypatch.setattr(sat, "_observe_sentinel1", lambda *args: None)
    result = run(sat.fetch_indices(geojson=PLOT))
    assert result.ndvi is None
    assert result.ndwi is None
    assert result.reason == "auth_failed"


def test_observation_window_is_forwarded():
    client = FakeClient(sat.sample_optical())
    run(sat.fetch_indices(geojson=PLOT, analysis_date=date(2026, 10, 20), client=client))
    _, start, end = client.calls[0]
    assert start.isoformat() == "2026-10-10"
    assert end.isoformat() == "2026-10-20"


def test_fetch_acquisitions_sorts_deduplicates_and_filters_mocked_collection():
    bounds = tuple(sat.validate_polygon(PLOT).bounds)
    client = FakeTimeSeriesClient(
        [
            sat.SatelliteAcquisition("scene-b", "2026-01-20", 0.55, 0.12, 92, "good", bounds=bounds),
            sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good", bounds=bounds),
            sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good", bounds=bounds),
            sat.SatelliteAcquisition("scene-outside", "2025-12-31", 0.9, 0.4, 99, "good", bounds=bounds),
            sat.SatelliteAcquisition("radar-scene", "2026-01-15", None, None, None, "radar_fallback", "sentinel-1", bounds=bounds),
        ]
    )

    result = run(
        sat.fetch_acquisitions(
            geojson=PLOT,
            start_date="2026-01-01",
            end_date="2026-01-31",
            client=client,
        )
    )

    assert [item.scene_id for item in result] == ["scene-a", "scene-b"]
    assert [item.observed_at for item in result] == ["2026-01-10", "2026-01-20"]
    assert result[0].bounds == bounds
    assert client.calls[0][1].isoformat() == "2026-01-01"
    assert client.calls[0][2].isoformat() == "2026-01-31"


def test_fetch_acquisitions_supports_max_count_without_requerying():
    client = FakeTimeSeriesClient(
        [
            sat.SatelliteAcquisition("scene-a", "2026-01-01", 0.4, 0.1, 90, "good"),
            sat.SatelliteAcquisition("scene-b", "2026-01-02", 0.5, 0.2, 90, "good"),
        ]
    )
    result = run(sat.fetch_acquisitions(geojson=PLOT, start_date="2026-01-01", end_date="2026-01-03", client=client, max_acquisitions=1))
    assert len(result) == 1
    assert len(client.calls) == 1


def test_analysis_report_complete_reuses_acquisitions_and_is_json_serializable():
    bounds = tuple(sat.validate_polygon(PLOT).bounds)
    acquisitions = [
        sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good", bounds=bounds),
        sat.SatelliteAcquisition("scene-b", "2026-01-20", 0.55, 0.12, 92, "good", bounds=bounds),
    ]
    spatial = sat.SatelliteSpatialDifference(
        "scene-a", "scene-b", "2026-01-10", "2026-01-20", "ndvi.png", "ndmi.png", 88, 88, 92, "good", bounds,
        {"grid_alignment": "later_scene_B8_projection"},
    )
    time_client = FakeTimeSeriesClient(acquisitions)
    spatial_client = FakeSpatialDifferenceClient(spatial)
    result = run(
        sat.build_satellite_analysis_report(
            geojson=PLOT,
            start_date="2026-01-01",
            end_date="2026-01-31",
            include_spatial_difference=True,
            generate_overlays=True,
            client=time_client,
            spatial_client=spatial_client,
        )
    )
    json.dumps(result)
    assert result["status"] == "complete"
    assert [item["scene_id"] for item in result["available_acquisitions"]] == ["scene-a", "scene-b"]
    assert result["temporal_comparison"]["ndvi_change"] == 0.13
    assert result["temporal_comparison"]["ndmi_change"] == -0.06
    assert result["spatial_difference"]["overlay_paths"] == {"ndvi_delta": "ndvi.png", "ndmi_delta": "ndmi.png"}
    assert spatial_client.calls[0][3] is True


def test_analysis_report_partial_selection_preserves_missing_reason():
    client = FakeTimeSeriesClient([sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good")])
    result = run(
        sat.build_satellite_analysis_report(
            geojson=PLOT,
            start_date="2026-01-01",
            end_date="2026-01-31",
            earlier_scene_id="scene-a",
            later_scene_id="missing",
            client=client,
        )
    )
    assert result["status"] == "partial"
    assert result["temporal_comparison"] is None
    assert "later_scene_not_available" in result["missing_data_reasons"]
    assert "two_selected_scenes_required" in result["missing_data_reasons"]


def test_analysis_report_missing_data_is_explicit_and_does_not_fabricate():
    result = run(
        sat.build_satellite_analysis_report(
            geojson=PLOT,
            start_date="2026-01-01",
            end_date="2026-01-31",
            client=FakeTimeSeriesClient([]),
        )
    )
    assert result["status"] == "no_data"
    assert result["available_acquisitions"] == []
    assert result["temporal_comparison"] is None
    assert result["spatial_difference"] is None
    assert result["missing_data_reasons"] == ["no_valid_sentinel2_acquisitions"]


def test_batched_feature_response_matches_previous_normalization():
    geometry = sat.validate_polygon(PLOT)
    start = date(2026, 1, 1)
    end = date(2026, 1, 31)
    raw = [
        sat.SatelliteAcquisition("scene-b", "2026-01-20", 0.55, 0.12, 92, "good"),
        sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good"),
        sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good"),
    ]
    previous_path = sat._normalize_acquisitions(raw, geometry, start, end)
    batched_features = [
        {"properties": {"scene_id": "scene-b", "observed_ms": 1768867200000, "ndvi": 0.55, "ndmi": 0.12, "valid_fraction": 0.92}},
        {"properties": {"scene_id": "scene-a", "observed_ms": 1768003200000, "ndvi": 0.42, "ndmi": 0.18, "valid_fraction": 0.88}},
        {"properties": {"scene_id": "scene-a", "observed_ms": 1768003200000, "ndvi": 0.42, "ndmi": 0.18, "valid_fraction": 0.88}},
    ]
    optimized_path = sat._parse_batched_features(batched_features, geometry, start, end)

    assert [(item.scene_id, item.observed_at, item.ndvi, item.ndmi, item.valid_pixel_pct, item.quality) for item in optimized_path] == [
        (item.scene_id, item.observed_at, item.ndvi, item.ndmi, item.valid_pixel_pct, item.quality)
        for item in previous_path
    ]


def test_batched_feature_response_preserves_nulls_and_quality():
    geometry = sat.validate_polygon(PLOT)
    result = sat._parse_batched_features(
        [
            {"properties": {"scene_id": "cloudy", "observed_ms": 1791372116371, "ndvi": None, "ndmi": None, "valid_fraction": 0.0}},
            {"properties": {"scene_id": "partial", "observed_ms": 1791804118187, "ndvi": 0.4, "ndmi": None, "valid_fraction": 0.69}},
        ],
        geometry,
        date(2026, 1, 1),
        date(2026, 12, 31),
    )
    assert result[0].ndvi is None and result[0].ndmi is None
    assert result[0].valid_pixel_pct == 0.0
    assert result[0].quality == "low_valid_pixels"
    assert result[1].ndvi == 0.4 and result[1].ndmi is None
    assert result[1].valid_pixel_pct == 69.0
    assert result[1].quality == "low_valid_pixels"
    assert result[0].quality_details["processing"] == "server_side_batched"


def test_earth_engine_temporal_path_receives_deterministic_max_count(monkeypatch):
    calls = []

    def fake_series(geometry, start, end, max_acquisitions=None):
        calls.append((start, end, max_acquisitions))
        return [sat.SatelliteAcquisition("scene-a", "2026-01-01", 0.4, 0.1, 90, "good")]

    monkeypatch.setattr(sat, "_observe_earth_engine_series", fake_series)
    result = run(
        sat.fetch_acquisitions(
            geojson=PLOT,
            start_date="2026-01-01",
            end_date="2026-01-31",
            max_acquisitions=1,
        )
    )
    assert len(result) == 1
    assert calls == [(date(2026, 1, 1), date(2026, 1, 31), 1)]


def test_compare_acquisitions_returns_raw_index_changes_and_shared_coverage():
    bounds = tuple(sat.validate_polygon(PLOT).bounds)
    earlier = sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good", bounds=bounds)
    later = sat.SatelliteAcquisition("scene-b", "2026-01-20", 0.55, 0.12, 75, "good", bounds=bounds)

    result = sat.compare_acquisitions(earlier, later)

    assert result.ndvi_change == 0.13
    assert result.ndmi_change == -0.06
    assert result.valid_pixel_pct == 75
    assert result.quality == "compatible"
    assert result.earlier_scene_id == "scene-a"
    assert result.later_scene_id == "scene-b"
    assert result.bounds == bounds


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("quality", "low_valid_pixels", "observation_quality_not_good"),
        ("valid_pixel_pct", 69, "observation_coverage_below_threshold"),
        ("ndvi", None, "observation_indices_missing"),
        ("ndmi", None, "observation_indices_missing"),
    ],
)
def test_compare_acquisitions_rejects_incompatible_quality(field, value, reason):
    bounds = tuple(sat.validate_polygon(PLOT).bounds)
    earlier = sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good", bounds=bounds)
    later_kwargs = {"scene_id": "scene-b", "observed_at": "2026-01-20", "ndvi": 0.55, "ndmi": 0.12, "valid_pixel_pct": 75, "quality": "good", "bounds": bounds}
    later_kwargs[field] = value
    later = sat.SatelliteAcquisition(**later_kwargs)

    with pytest.raises(sat.IncompatibleSatelliteObservations, match=reason):
        sat.compare_acquisitions(earlier, later)


def test_compare_acquisitions_rejects_geometry_source_and_date_mismatch():
    bounds = tuple(sat.validate_polygon(PLOT).bounds)
    earlier = sat.SatelliteAcquisition("scene-a", "2026-01-10", 0.42, 0.18, 88, "good", bounds=bounds)
    with pytest.raises(sat.IncompatibleSatelliteObservations, match="geometry_mismatch"):
        sat.compare_acquisitions(earlier, sat.SatelliteAcquisition("scene-b", "2026-01-20", 0.5, 0.2, 88, "good", bounds=(-8, 33, -7, 34)))
    with pytest.raises(sat.IncompatibleSatelliteObservations, match="dates_not_chronological"):
        sat.compare_acquisitions(earlier, sat.SatelliteAcquisition("scene-b", "2026-01-05", 0.5, 0.2, 88, "good", bounds=bounds))
    with pytest.raises(sat.IncompatibleSatelliteObservations, match="optical_sentinel2_only"):
        sat.compare_acquisitions(earlier, sat.SatelliteAcquisition("radar", "2026-01-20", None, None, None, "radar_fallback", "sentinel-1", bounds=bounds))


def test_compute_spatial_difference_sign_and_intersection_mask():
    delta_ndvi, delta_ndmi, shared_pct = sat.compute_spatial_difference(
        [0.20, 0.40, 0.60],
        [0.30, 0.10, 0.70],
        [0.10, 0.20, 0.30],
        [0.20, 0.10, 0.10],
        [True, True, False],
        [True, False, True],
    )
    assert delta_ndvi == [0.1, None, None]
    assert delta_ndmi == [0.1, None, None]
    assert shared_pct == 33.33


def test_compute_spatial_difference_rejects_unaligned_grids():
    with pytest.raises(sat.IncompatibleSatelliteObservations, match="spatial_grid_shape_mismatch"):
        sat.compute_spatial_difference([0.2], [0.3, 0.4], [0.1], [0.2], [True], [True])


def test_compare_scene_maps_uses_explicit_ids_and_preserves_bounds():
    bounds = tuple(sat.validate_polygon(PLOT).bounds)
    expected = sat.SatelliteSpatialDifference(
        "scene-a", "scene-b", "2026-01-01", "2026-01-20", None, None, 88.0, 90.0, 92.0, "good", bounds
    )
    client = FakeSpatialDifferenceClient(expected)
    result = run(
        sat.compare_scene_maps(
            geojson=PLOT,
            earlier_scene_id="scene-a",
            later_scene_id="scene-b",
            generate_overlay=False,
            client=client,
        )
    )
    assert result is expected
    assert client.calls[0][1:] == ("scene-a", "scene-b", False)
    assert result.bounds == bounds


def test_compare_scene_maps_rejects_same_or_missing_scene_selection():
    with pytest.raises(sat.IncompatibleSatelliteObservations, match="distinct_scene_ids_required"):
        run(sat.compare_scene_maps(geojson=PLOT, earlier_scene_id="scene-a", later_scene_id="scene-a"))
    with pytest.raises(sat.IncompatibleSatelliteObservations, match="distinct_scene_ids_required"):
        run(sat.compare_scene_maps(geojson=PLOT, earlier_scene_id="", later_scene_id="scene-b"))


def test_compare_scene_maps_rejects_low_quality_client_result():
    bounds = tuple(sat.validate_polygon(PLOT).bounds)
    client = FakeSpatialDifferenceClient(
        sat.SatelliteSpatialDifference(
            "scene-a", "scene-b", "2026-01-01", "2026-01-20", None, None, 40.0, 90.0, 90.0, "low_valid_pixels", bounds
        )
    )
    with pytest.raises(sat.IncompatibleSatelliteObservations, match="observation_quality_not_good"):
        run(
            sat.compare_scene_maps(
                geojson=PLOT,
                earlier_scene_id="scene-a",
                later_scene_id="scene-b",
                generate_overlay=False,
                client=client,
            )
        )


def _rgba_png() -> bytes:
    """Small 2x1 PNG with one transparent and one opaque pixel."""
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 2, 1, 8, 6, 0, 0, 0)
    scanline = b"\x00\x00\x00\x00\x00\xff\xff\x00\x00"
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(scanline)) + chunk(b"IEND", b"")


class FakeOverlayImage:
    def __init__(self):
        self.clip_region = None
        self.visualize_args = None

    def clip(self, region):
        self.clip_region = region
        return self

    def visualize(self, **kwargs):
        self.visualize_args = kwargs
        return self

    def getThumbURL(self, params):
        self.thumb_params = params
        return "https://example.invalid/ndvi.png"


def test_overlay_clips_to_polygon_and_writes_alpha_png(request, monkeypatch):
    overlay_dir = Path("artifacts")
    image = FakeOverlayImage()
    monkeypatch.setattr(settings, "satellite_overlay_dir", str(overlay_dir))
    monkeypatch.setattr(sat.urllib.request, "urlretrieve", lambda url, target: Path(target).write_bytes(_rgba_png()))

    result = sat._render_overlay(
        image,
        "polygon-region",
        "2026-11-01",
        object(),
        plot_id="MA-001",
        scene_id="S2A_TEST_SCENE",
        geometry_digest="geometry-a",
    )

    output = Path(result)
    request.addfinalizer(lambda: output.unlink(missing_ok=True))
    assert output.is_file()
    assert image.clip_region == "polygon-region"
    assert image.thumb_params == {"region": "polygon-region", "dimensions": 1024, "format": "png"}
    assert image.visualize_args["forceRgbOutput"] is True
    png = output.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">I", png[16:20])[0] == 2
    assert struct.unpack(">I", png[20:24])[0] == 1
    assert png[25] == 6  # RGBA color type


def test_ndvi_and_ndmi_overlay_types_use_distinct_palettes_and_metadata(request, monkeypatch):
    overlay_dir = Path("artifacts")
    monkeypatch.setattr(settings, "satellite_overlay_dir", str(overlay_dir))
    monkeypatch.setattr(sat.urllib.request, "urlretrieve", lambda url, target: Path(target).write_bytes(_rgba_png()))
    outputs = []

    for index_type in ("ndvi", "ndmi"):
        image = FakeOverlayImage()
        result = sat._render_overlay(
            image,
            "polygon-region",
            "2026-11-01",
            object(),
            index_type=index_type,
            plot_id="MA-001",
            scene_id="S2A_TEST_SCENE",
            geometry_digest="geometry-a",
        )
        outputs.append(Path(result))
        assert outputs[-1].name.startswith(f"{index_type}_MA-001_")
        assert image.visualize_args["min"] == -1
        assert image.visualize_args["max"] == 1
        assert image.visualize_args["palette"] == list(sat.OVERLAY_PALETTES[index_type])
        assert image.clip_region == "polygon-region"

        metadata = sat._overlay_metadata(index_type, "2026-11-01", (-7.5898, 33.5731, -7.5888, 33.574), str(outputs[-1]))
        assert metadata["index_type"] == index_type
        assert metadata["observed_at"] == "2026-11-01"
        assert metadata["bounds"] == [-7.5898, 33.5731, -7.5888, 33.574]
        assert metadata["palette"] == list(sat.OVERLAY_PALETTES[index_type])
        assert metadata["path"] == str(outputs[-1])

    request.addfinalizer(lambda: [path.unlink(missing_ok=True) for path in outputs])


def test_delta_overlays_use_symmetric_diverging_palette_and_transparency(request, monkeypatch):
    overlay_dir = Path("artifacts")
    image = FakeOverlayImage()
    monkeypatch.setattr(settings, "satellite_overlay_dir", str(overlay_dir))
    monkeypatch.setattr(sat.urllib.request, "urlretrieve", lambda url, target: Path(target).write_bytes(_rgba_png()))
    result = sat._render_overlay(
        image,
        "polygon-region",
        "2026-11-01",
        object(),
        index_type="ndvi_delta",
        plot_id="MA-001",
        scene_id="scene-a__scene-b",
        geometry_digest="geometry-a",
    )
    output = Path(result)
    request.addfinalizer(lambda: output.unlink(missing_ok=True))
    assert output.name.startswith("ndvi_delta_MA-001_")
    assert image.visualize_args["min"] == -1
    assert image.visualize_args["max"] == 1
    assert image.visualize_args["palette"] == list(sat.OVERLAY_PALETTES["ndvi_delta"])
    assert output.read_bytes()[25] == 6  # RGBA color type with transparency channel


def test_overlay_filename_is_stable_and_distinct_per_plot_geometry_and_scene():
    first = sat._overlay_filename(
        "2026-11-01", plot_id="MA-001", scene_id="scene-a", geometry_digest="geometry-a"
    )
    same_inputs = sat._overlay_filename(
        "2026-11-01", plot_id="MA-001", scene_id="scene-a", geometry_digest="geometry-a"
    )
    other_plot = sat._overlay_filename(
        "2026-11-01", plot_id="MA-002", scene_id="scene-a", geometry_digest="geometry-b"
    )
    ndmi = sat._overlay_filename(
        "2026-11-01", index_type="ndmi", plot_id="MA-001", scene_id="scene-a", geometry_digest="geometry-a"
    )
    assert first == same_inputs
    assert first != other_plot
    assert first != ndmi
    assert ndmi.startswith("ndmi_MA-001_")
    assert first.endswith(".png") is False


def test_overlay_failure_returns_null_and_cleans_temporary_file(monkeypatch):
    overlay_dir = Path("artifacts")
    monkeypatch.setattr(settings, "satellite_overlay_dir", str(overlay_dir))

    def fail(*args):
        raise OSError("download failed")

    monkeypatch.setattr(sat.urllib.request, "urlretrieve", fail)
    result = sat._render_overlay(
        FakeOverlayImage(),
        "polygon-region",
        "2026-11-01",
        object(),
        plot_id="MA-001",
        geometry_digest="geometry-a",
    )
    assert result is None
    assert not any(overlay_dir.glob("ndvi_MA-001_geometry-a_2026-11-01_*.png"))


def test_observation_bounds_remain_west_south_east_north():
    assert tuple(sat.validate_polygon(PLOT).bounds) == (-7.5898, 33.5731, -7.5888, 33.574)


def test_spatial_difference_keeps_projection_alignment_lazy():
    source = inspect.getsource(sat._observe_earth_engine_spatial_difference)
    assert "reproject(target_projection)" not in source
    assert source.count("setDefaultProjection(target_projection)") == 6
    assert "crs=target_projection" in source
