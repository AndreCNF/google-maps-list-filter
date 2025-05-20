import re
from typing import Any, Dict, Optional
import backoff
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from tqdm.auto import tqdm
from loguru import logger
from geopy.geocoders import Nominatim, ArcGIS
from geopy.exc import GeopyError


def filter_geojson_by_geometry(
    places_geojson: Dict[str, Any], filter_geometry: Dict[str, Any]
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


def _geocode_with_retry(query: str, gmaps_client: Any) -> list[dict]:
    """
    Wraps gmaps_client.geocode in an exponential backoff retry on exceptions.

    Args:
        query (str): The geocode query string.
        gmaps_client (Any): Authenticated Google Maps client.

    Returns:
        list[dict]: Geocoding results from the API.
    """

    @backoff.on_exception(backoff.expo, Exception, max_time=60, logger=logger)
    def call():
        return gmaps_client.geocode(query)

    return call()


@backoff.on_exception(backoff.expo, GeopyError, max_time=60, logger=logger)
def _nominatim_geocode(query: str, osm_email: str) -> Optional[dict[str, Any]]:
    """
    Fallback geocoding using OpenStreetMap Nominatim service with retry on errors.

    Args:
        query (str): The geocode query string.
        osm_email (str): Email address for Nominatim usage policy compliance.

    Returns:
        Optional[dict[str, Any]]: Geocoding result with 'lat', 'lon', and 'address', or None if not found.
    """
    geolocator = Nominatim(user_agent=osm_email)
    try:
        location = geolocator.geocode(query)
        if location is None:
            return None
        return {
            "lat": location.latitude,
            "lon": location.longitude,
            "address": location.address,
        }
    except GeopyError as e:
        logger.error(f"Nominatim error for query: {query}, error: {e}")
        return None


# Add ArcGIS fallback geocoding
@backoff.on_exception(backoff.expo, GeopyError, max_time=60, logger=logger)
def _arcgis_geocode(query: str) -> Optional[dict[str, Any]]:
    """
    Fallback geocoding using ArcGIS service with retry on errors.

    Args:
        query (str): The geocode query string.

    Returns:
        Optional[dict[str, Any]]: Geocoding result or None if not found.
    """
    geolocator = ArcGIS()
    try:
        location = geolocator.geocode(query)
        if location is None:
            return None
        return {
            "lat": location.latitude,
            "lon": location.longitude,
            "address": getattr(location, "address", ""),
        }
    except GeopyError as e:
        logger.error(f"ArcGIS error for query: {query}, error: {e}")
        return None


def is_dms(coord: str) -> bool:
    """
    Detect if `coord` is in valid DMS format for latitude and longitude.
    Examples of accepted format:
      4°41'02.9"N 74°02'54.5"W
      04°41'02.90 S, 074°02'54.50 E

    Args:
        coord (str): Coordinate string to check.

    Returns:
        bool: True if the coordinate is in valid DMS format, False otherwise.
    """
    # Regex breakdown:
    #  - Degrees: 1–3 digits (00 to 180 for lon, 00 to 90 for lat but we won't strictly enforce ranges here)
    #  - Minutes: exactly 2 digits (00 to 59)
    #  - Seconds: 2 digits plus optional fraction (00.0 to 59.999...)
    #  - Direction: one of N, S, E, or W
    dms_pattern = re.compile(
        r"""
        ^\s*                                  # optional leading whitespace
        ([0-9]{1,3})°([0-5][0-9])'(\d{2}(?:\.\d+)?)"  # latitude DMS
        \s*([NS])                             # N or S
        [,\s]+                                # separator (comma and/or space)
        ([0-9]{1,3})°([0-5][0-9])'(\d{2}(?:\.\d+)?)"  # longitude DMS
        \s*([EW])                             # E or W
        \s*$                                  # optional trailing whitespace
    """,
        re.VERBOSE | re.IGNORECASE,
    )

    return bool(dms_pattern.match(coord))


def geocode_places(
    rows: list[dict[str, str]], gmaps_client: Any, osm_email: str
) -> dict[str, Any]:
    """
    Uses a Google Maps client to geocode place titles and returns a GeoJSON FeatureCollection.

    Args:
        rows (list[dict]): List of CSV rows with 'Title' and 'URL' fields.
        gmaps_client (googlemaps.Client): Authenticated Google Maps client.
        osm_email (str): Email address for Nominatim usage policy compliance.

    Returns:
        dict: GeoJSON FeatureCollection of geocoded points.
    """
    features: list[dict] = []
    for row in tqdm(rows, desc="Geocoding places"):
        title = row.get("Title", "")
        if not title:
            logger.warning("Missing title for row: {row}", row=row)
            continue
        elif is_dms(title):
            # Skip DMS coordinates
            logger.warning("Skipping DMS coordinates in title: {title}", title=title)
            continue
        url = row.get("URL", "")
        if not url:
            logger.warning("Missing URL for row: {row}", row=row)
            continue
        try:
            # Including the URL in the geocode query to improve accuracy (with backoff)
            results = _geocode_with_retry(f"{title} {url}", gmaps_client)
            if not results:
                # Let's try without the URL
                results = _geocode_with_retry(title, gmaps_client)
            if not results:
                # Let's try with just the URL
                results = _geocode_with_retry(url, gmaps_client)
            if results:
                # Process the Google Maps results
                first_result = results[0]
                loc = first_result.get("geometry", {}).get("location", {})
                lat = loc.get("lat")
                lon = loc.get("lng")
                if lat is None or lon is None:
                    logger.warning(
                        "Incomplete location data for title: {title}", title=title
                    )
                    continue
                formatted_address = first_result.get("formatted_address", "")
                categories = first_result.get("types", [])
            else:
                try:
                    # Fallback to Nominatim if Google Maps returns no results
                    nom_res = _nominatim_geocode(title, osm_email)
                except:
                    nom_res = None
                if nom_res:
                    lat = nom_res["lat"]
                    lon = nom_res["lon"]
                    formatted_address = nom_res.get("address", "")
                else:
                    # Fallback to ArcGIS if Nominatim fails
                    arc_res = _arcgis_geocode(title)
                    if arc_res:
                        lat = arc_res["lat"]
                        lon = arc_res["lon"]
                        formatted_address = arc_res.get("address", "")
                    else:
                        logger.warning(
                            f"Fallback ArcGIS returned no results for title: {title}"
                        )
                        # Skip this row if no geocoding result
                        continue
                categories = []
            if formatted_address:
                title = f"{title} | {formatted_address}"
            feature = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "location": {"name": title},
                    "url": url,
                    "categories": categories,
                },
            }
            features.append(feature)
        except Exception as e:
            logger.error(
                "Google Maps API error for title: {title}, error: {error}",
                title=title,
                error=str(e),
            )
    return {"type": "FeatureCollection", "features": features}
