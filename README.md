# google-maps-list-filter

<p align="center">
  <img src="images/app_preview.png" width="600">
</p>

<p align="center">
  <a href="https://github.com/charliermarsh/ruff">
    <img src="https://camo.githubusercontent.com/bb88127790fb054cba2caf3f3be2569c1b97bb45a44b47b52d738f8781a8ede4/68747470733a2f2f696d672e736869656c64732e696f2f656e64706f696e743f75726c3d68747470733a2f2f7261772e67697468756275736572636f6e74656e742e636f6d2f636861726c6965726d617273682f727566662f6d61696e2f6173736574732f62616467652f76312e6a736f6e" alt="Code style: ruff">
  </a>
  <a href="https://maps-list-filter.streamlit.app/">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg" alt="Streamlit App">
  </a>
</p>

Filter through long lists of Google Maps saved places, sharing them in an organized, geofenced way with AI-generated descriptions and titles.

## Features

- **Geocode Saved Places**: Primary geocoding via Google Maps API, with fallback to OpenStreetMap Nominatim and ArcGIS for missing results.
- **Spatial Filtering**: Interactive map to draw polygons and filter points within a region.
- **AI-powered Descriptions**: Generate concise titles and descriptions using OpenAI Search API.
- **Export Options**: Download filtered results as GeoJSON for mapping or CSV for Google My Maps.

## Setup

### Prerequisites

- Python 3.13
- API keys:
  - `GOOGLE_MAPS_API_KEY`
  - `OSM_EMAIL` (for Nominatim)
  - `OPENAI_API_KEY`

### Installation

```bash
# Clone repository
git clone https://github.com/<username>/google-maps-list-filter.git
cd google-maps-list-filter

# Install dependencies using uv
uv sync

# Install the package locally
uv pip install -e .
```

### Running the App

```bash
# Launch Streamlit application
uv run streamlit run google_maps_list_filter/app.py
```

## Project Structure

```
google_maps_list_filter/
├── app.py                # Streamlit orchestrator: upload, geocode, filter, describe, export
├── io_utils.py           # I/O utilities: unzip Takeout, list and read saved CSVs
├── map_utils.py          # Geospatial utilities: geocode_rows, filter by drawing
├── description_generator.py # AI descriptions: OpenAI Search API integration
└── __init__.py

tests/
├── test_io_utils.py
├── test_map_utils.py
└── test_description_generator.py
```

## Main Workflow

1. **Upload** Google Takeout ZIP containing your Saved Places CSVs.
2. **Extract & Read**: IO utilities decompress and parse CSV rows.
3. **Geocode**: `geocode_rows` attempts Google Maps API first, then Nominatim fallback.
4. **Draw & Filter**: Streamlit displays a folium map; user draws polygon to filter points.
5. **Describe**: For filtered features, `generate_place_description` uses OpenAI Search API to produce titles, descriptions, and categorize.
6. **Display & Download**: Visualize filtered points on map; download GeoJSON or CSV for further use.

## Contributing

Contributions welcome! Feel free to open issues or pull requests.
