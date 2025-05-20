import pytest
from google_maps_list_filter.map_utils import filter_geojson_by_geometry


def make_feature(coord, name="place"):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": coord},
        "properties": {"location": {"name": name}},
    }


def test_filter_geojson_by_geometry_valid():
    """
    Test filtering features by a simple square polygon geometry.
    """
    # Define a square from (0,0) to (10,10)
    filter_geom = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
    }
    # Feature inside polygon
    inside = make_feature([5, 5], name="inside")
    # Feature outside polygon
    outside = make_feature([15, 15], name="outside")
    places_geojson = {"type": "FeatureCollection", "features": [inside, outside]}

    result = filter_geojson_by_geometry(places_geojson, filter_geom)
    features = result["features"]
    assert len(features) == 1
    props = features[0]["properties"]
    assert props["location"]["name"] == "inside"


def test_filter_geojson_by_geometry_multipolygon():
    """
    Test filtering with a MultiPolygon geometry.
    """
    # Define two small squares
    coords = [
        [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]],
        [[[10, 10], [10, 12], [12, 12], [12, 10], [10, 10]]],
    ]
    filter_geom = {"type": "MultiPolygon", "coordinates": coords}
    inside1 = make_feature([1, 1], name="inside1")
    inside2 = make_feature([11, 11], name="inside2")
    outside = make_feature([5, 5], name="outside")
    places_geojson = {
        "type": "FeatureCollection",
        "features": [inside1, inside2, outside],
    }

    result = filter_geojson_by_geometry(places_geojson, filter_geom)
    names = {feat["properties"]["location"]["name"] for feat in result["features"]}
    assert names == {"inside1", "inside2"}


def test_filter_geojson_by_geometry_invalid_geometry():
    """
    Test that a ValueError is raised for non-polygon geometries.
    """
    # Point geometry passed instead of Polygon/MultiPolygon
    invalid_geom = {"type": "Point", "coordinates": [0, 0]}
    places_geojson = {"type": "FeatureCollection", "features": []}
    with pytest.raises(ValueError):
        filter_geojson_by_geometry(places_geojson, invalid_geom)
