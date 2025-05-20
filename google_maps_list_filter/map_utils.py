from typing import Any, Dict
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from geojson import FeatureCollection
from loguru import logger


def filter_geojson_by_geometry(
    places_geojson: Dict[str, Any],
    filter_geometry: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Filters a GeoJSON FeatureCollection of point features by a provided polygon geometry.

    Args:
        places_geojson (Dict[str, Any]): The original GeoJSON FeatureCollection containing point features.
        filter_geometry (Dict[str, Any]): A GeoJSON geometry object (Polygon or MultiPolygon) to filter points by.

    Returns:
        Dict[str, Any]: A new GeoJSON FeatureCollection containing only the input features whose points fall within the filter_geometry.
    """
    # Convert filter geometry to a Shapely shape
    polygon = shape(filter_geometry)
    if not isinstance(polygon, (Polygon, MultiPolygon)):
        error_msg = "filter_geometry must be a Polygon or MultiPolygon GeoJSON geometry"
        logger.error(error_msg)
        raise ValueError(error_msg)

    filtered_features: list[dict] = []
    for feature in places_geojson.get("features", []):
        geom = feature.get("geometry")
        if not geom:
            continue
        point = shape(geom)
        if not isinstance(point, Point):
            logger.warning("Skipped non-Point geometry: {geom}", geom=geom)
            continue
        if polygon.contains(point):
            # Retain the original feature dict
            filtered_features.append(feature)

    logger.info(
        "Filtered {total} features down to {count} features",
        total=len(places_geojson.get("features", [])),
        count=len(filtered_features),
    )
    # Return a GeoJSON-like dict
    return {"type": "FeatureCollection", "features": filtered_features}
