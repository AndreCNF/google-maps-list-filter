import os
import tempfile
import hashlib
import json
import io
import csv
from pathlib import Path
from tqdm.auto import tqdm

import streamlit as st
import folium
import googlemaps
from dotenv import load_dotenv
from streamlit_folium import st_folium
from folium.plugins import Draw

from google_maps_list_filter.io_utils import (
    extract_zip,
    list_saved_csvs,
    read_saved_csv,
)
from google_maps_list_filter.map_utils import filter_geojson_by_geometry, geocode_places
from google_maps_list_filter.description_generator import generate_place_description

# Load environment variables
load_dotenv()

# Add wide layout configuration for Streamlit app
st.set_page_config(page_title="Google Maps Saved Places Filter", layout="wide")


# ----- CACHING HELPERS -----
@st.cache_data(show_spinner=False)
def geocode_rows(rows, api_key: str, osm_email: str) -> dict:
    """
    Geocode a list of place rows to GeoJSON, cached by rows-hash + credentials.
    """
    client = googlemaps.Client(key=api_key)
    return geocode_places(rows, client, osm_email)


# ----- UTILITIES -----
def hash_bytes(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


# ----- APP BEGINS -----
def main():
    st.title("Google Maps Saved Places Filter")
    st.info(
        "In order to get your saved places from Google Maps, you need to download your Google Takeout ZIP file:\n"
        "1. Go to [Google Takeout](https://takeout.google.com/)\n"
        "2. Make sure “Saved” is checked in “Create A New Export.”\n"
        "3. Click Next Step.\n"
        "4. Click Create Export.\n\n"
        "More information on how to download your Google Takeout ZIP file can be found [here](https://support.google.com/maps/answer/7280933?hl=en&co=GENIE.Platform%3DDesktop#zippy=%2Cexport-your-saved-lists).\n"
    )

    # --- Step 0: Credentials ---
    # Retrieve any environment defaults
    gmaps_default = os.getenv("GOOGLE_MAPS_API_KEY", "")
    osm_default = os.getenv("OSM_EMAIL", "")
    openai_default = os.getenv("OPENAI_API_KEY", "")

    # Credential inputs in three columns
    col1, col2, col3 = st.columns(3)
    with col1:
        gmaps_key = st.text_input(
            "Google Maps API Key",
            type="password",
            key="gmaps_key",
            value=st.session_state.get("gmaps_key", gmaps_default),
        )
    with col2:
        osm_email = st.text_input(
            "OpenStreetMap Email",
            type="password",
            key="osm_email",
            value=st.session_state.get("osm_email", osm_default),
        )
    with col3:
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            key="openai_key",
            value=st.session_state.get("openai_key", openai_default),
        )
    # Instructions expander below inputs, laid out in three columns
    with st.expander("How to get these credentials", expanded=False):
        ins_col1, ins_col2, ins_col3 = st.columns(3)
        with ins_col1:
            st.markdown("### Google Maps API Key")
            st.markdown(
                "To get a Google Maps API key:\n"
                "1. Go to the [Google Cloud Console](https://console.cloud.google.com/google/maps-apis/overview).\n"
                "2. Create a project or select one.\n"
                "3. Enable the Geocoding API.\n"
                "4. Generate and copy an API key."
            )
        with ins_col2:
            st.markdown("### OpenStreetMap Email")
            st.markdown(
                "To get an OpenStreetMap email:\n"
                "1. Go to [OpenStreetMap](https://www.openstreetmap.org/) and log in.\n"
                "2. Use your account email."
            )
        with ins_col3:
            st.markdown("### OpenAI API Key")
            st.markdown(
                "To get an OpenAI API key:\n"
                "1. Go to [OpenAI](https://platform.openai.com/signup).\n"
                "2. Create an account or log in.\n"
                "3. Generate and copy an API key."
            )

    # --- Step 1: Upload ZIP ---
    uploaded = st.file_uploader(
        "Upload your Google Takeout ZIP with 'Saved' folder", type="zip"
    )
    if not uploaded:
        return
    uploaded_hash = hash_bytes(uploaded.getvalue())
    # New upload? extract once and reset state
    if st.session_state.get("uploaded_hash") != uploaded_hash:
        tmpdir = tempfile.mkdtemp()
        zip_path = Path(tmpdir) / "takeout.zip"
        zip_path.write_bytes(uploaded.getvalue())
        extract_zip(str(zip_path), tmpdir)
        csv_paths = list_saved_csvs(tmpdir)
        if not csv_paths:
            st.error("No CSVs found in 'Saved' folders of your ZIP.")
            return
        st.session_state.update(
            {
                "uploaded_hash": uploaded_hash,
                "tmpdir": tmpdir,
                "csv_paths": csv_paths,
                "geodata": None,
                "filtered": None,
                "descriptions_generated": False,
                "last_csv": None,
            }
        )

    # --- Step 2: Pick CSV List ---
    csv_names = [Path(p).stem for p in st.session_state.csv_paths]
    choice = st.selectbox("Select a saved list to filter", csv_names, key="csv_choice")
    selected = next(p for p in st.session_state.csv_paths if Path(p).stem == choice)
    # Reset downstream if list changes
    if st.session_state.last_csv != selected:
        st.session_state.update(
            {
                "last_csv": selected,
                "geodata": None,
                "filtered": None,
                "descriptions_generated": False,
            }
        )

    # --- Step 3: Geocode Rows ---
    if st.session_state.geodata is None:
        if st.button("Run geocode", key="run_geocode"):
            if not gmaps_key or not osm_email:
                st.error("Google Maps API key and OSM email are required to geocode.")
            else:
                rows = read_saved_csv(selected)
                geodata = geocode_rows(rows, gmaps_key, osm_email)
                st.session_state.geodata = geodata
    if st.session_state.geodata is None:
        return
    geodata = st.session_state.geodata

    # --- Step 4: Draw & Filter ---
    st.subheader("Map & Draw Filter Polygon")
    coords = [
        feat["geometry"]["coordinates"][::-1] for feat in geodata.get("features", [])
    ]
    if coords:
        lats, lons = zip(*coords)
        centroid = [sum(lats) / len(lats), sum(lons) / len(lons)]
        m = folium.Map(location=centroid, zoom_start=4)
    else:
        m = folium.Map(zoom_start=2)
    for feat in geodata.get("features", []):
        lon, lat = feat["geometry"]["coordinates"]
        name = feat["properties"]["location"]["name"]
        folium.Marker([lat, lon], popup=name).add_to(m)
    Draw(export=True).add_to(m)
    draw_result = st_folium(m, height=600, width=800)

    # Ensure 'filtered' always defined
    filtered = st.session_state.get("filtered")
    if draw_result and draw_result.get("last_active_drawing"):
        geom = draw_result["last_active_drawing"]["geometry"]
        if st.session_state.get("last_geom") != geom:
            if st.button("Apply filter", key="apply_filter"):
                filtered = filter_geojson_by_geometry(geodata, geom)
                st.session_state.filtered = filtered
                st.session_state.last_geom = geom
                st.session_state.descriptions_generated = False
    if not filtered:
        return

    # --- Step 5: Generate AI Descriptions ---
    st.subheader("AI-generated Descriptions")
    if not st.session_state.descriptions_generated:
        if st.button("Generate descriptions", key="gen_desc"):
            if not openai_key:
                st.error("OpenAI API key is required for descriptions.")
            else:
                features = filtered.get("features", [])
                progress = st.progress(0)
                total = len(features)
                for i, feat in tqdm(
                    enumerate(features), desc="Generating descriptions", total=total
                ):
                    title = feat["properties"]["location"]["name"]
                    cats = feat["properties"].get("categories", [])
                    try:
                        model = generate_place_description(title, cats, openai_key)
                        feat["properties"]["description"] = model.description
                        feat["properties"]["title"] = model.title
                        feat["properties"]["categories"] = model.categories
                    except Exception:
                        feat["properties"]["description"] = ""
                    progress.progress((i + 1) / total)
                st.session_state.filtered = filtered
                st.session_state.descriptions_generated = True
    else:
        st.info("Descriptions already generated.")

    # --- Step 6: Download ---
    st.subheader("Downloads")
    geojson_str = json.dumps(filtered, indent=2)
    st.download_button(
        "Download filtered GeoJSON",
        geojson_str,
        file_name="filtered_saved_places.geojson",
        mime="application/json",
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "description", "categories", "WKT"])
    for feat in filtered["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        props = feat.get("properties", {})
        name = props.get("title") or props.get("location", {}).get("name", "")
        desc = props.get("description", "")
        categories = props.get("categories", [])
        writer.writerow([name, desc, ", ".join(categories), f"POINT({lon} {lat})"])
    st.download_button(
        "Download CSV to import in Google My Maps",
        buf.getvalue(),
        file_name="filtered_saved_places_mymaps.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
