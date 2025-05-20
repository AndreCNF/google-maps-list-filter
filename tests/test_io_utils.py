import pytest
import json
import zipfile
from pathlib import Path

from google_maps_list_filter.io_utils import extract_saved_places_json, load_geojson


def test_load_geojson(tmp_path):
    """
    Test loading a valid GeoJSON file.
    """
    sample = {"type": "FeatureCollection", "features": []}
    file = tmp_path / "sample.json"
    file.write_text(json.dumps(sample))
    data = load_geojson(str(file))
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)
    assert data["features"] == []


def test_extract_saved_places_json(tmp_path):
    """
    Test extracting Saved Places.json from a ZIP archive.
    """
    nested = tmp_path / "takeout_folder"
    nested.mkdir()
    saved_file = nested / "Saved Places.json"
    sample = {"features": []}
    saved_file.write_text(json.dumps(sample))
    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.write(saved_file, arcname="some_folder/Saved Places.json")
    output_dir = tmp_path / "output"
    result_path = extract_saved_places_json(str(zip_path), str(output_dir))
    assert Path(result_path).exists()
    loaded = json.loads(Path(result_path).read_text())
    assert loaded == sample


def test_extract_saved_places_json_not_found(tmp_path):
    """
    Test that FileNotFoundError is raised when the JSON file is missing.
    """
    zip_path = tmp_path / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr("other_file.txt", "data")
    with pytest.raises(FileNotFoundError):
        extract_saved_places_json(str(zip_path), str(tmp_path))
