from app.core.geo import (
    centroid_lon_lat,
    coordinates_to_geojson,
    default_ma001_geojson,
    parse_plot_geom,
)


def test_coordinates_roundtrip():
    feature = coordinates_to_geojson(
        [[[-7.5, 33.5], [-7.4, 33.5], [-7.4, 33.6], [-7.5, 33.6], [-7.5, 33.5]]]
    )
    assert feature["geometry"]["type"] == "Polygon"
    center = centroid_lon_lat(feature)
    assert center is not None
    assert abs(center[0] + 7.45) < 0.1
    assert abs(center[1] - 33.55) < 0.1


def test_parse_ewkt():
    raw = "SRID=4326;POLYGON((-7.5898 33.5731, -7.5888 33.5731, -7.5888 33.5740, -7.5898 33.5740, -7.5898 33.5731))"
    feature = parse_plot_geom(raw)
    assert feature is not None
    assert feature["geometry"]["type"] == "Polygon"


def test_ma001_default():
    feature = default_ma001_geojson()
    assert centroid_lon_lat(feature) is not None
