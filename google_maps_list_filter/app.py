import tempfile
import json
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
from pathlib import Path
from loguru import logger

from .io_utils import extract_saved_places_json, load_geojson
from .map_utils import filter_geojson_by_geometry


def main() -> None:
    """
    Main function to run the Streamlit app for filtering Google Maps saved places.
    """
    st.title("Google Maps Saved Places Filter")

    uploaded_file = st.file_uploader(
        "Upload your Google Takeout ZIP file containing Saved Places.json", type="zip"
    )

    if uploaded_file:
        with tempfile.TemporaryDirectory() as tmpdir:  # type: ignore[no-untyped-call]
            zip_path = Path(tmpdir) / "takeout.zip"
            zip_path.write_bytes(uploaded_file.getvalue())
            try:
                json_path = extract_saved_places_json(str(zip_path), tmpdir)
                data = load_geojson(json_path)
            except Exception as e:
                st.error(f"Error processing file: {e}")
                logger.error("Error processing file: {error}", error=str(e))
                return

            # Prepare map
            coords = [
                feat["geometry"]["coordinates"][::-1]
                for feat in data.get("features", [])
            ]
            if coords:
                m = folium.Map(location=coords[0], zoom_start=12)
            else:
                m = folium.Map(zoom_start=2)

            # Add markers
            for feat in data.get("features", []):
                lon, lat = feat["geometry"]["coordinates"]
                name = feat["properties"]["location"]["name"]
                folium.Marker([lat, lon], popup=name).add_to(m)

            # Add draw plugin
            draw = Draw(export=True)
            draw.add_to(m)

            st.subheader("Draw a polygon to filter places")
            result = st_folium(m, height=600)

            # Handle drawing result
            if result and result.get("last_active_drawing"):
                filter_geom = result["last_active_drawing"]["geometry"]
                filtered = filter_geojson_by_geometry(data, filter_geom)

                st.subheader("Filtered Places")
                # Show filtered map
                fm = folium.Map(location=coords[0], zoom_start=12)
                for feat in filtered["features"]:
                    lon, lat = feat["geometry"]["coordinates"]
                    name = feat["properties"].get("location", {}).get("name", "")
                    folium.Marker(
                        [lat, lon], popup=name, icon=folium.Icon(color="green")
                    ).add_to(fm)
                st_folium(fm, height=400)

                # Download filtered GeoJSON
                geojson_str = json.dumps(filtered, indent=2)
                st.download_button(
                    label="Download filtered GeoJSON",
                    data=geojson_str,
                    file_name="filtered_saved_places.geojson",
                    mime="application/json",
                )


if __name__ == "__main__":
    main()
