import zipfile
import json
from pathlib import Path
from loguru import logger


def extract_saved_places_json(zip_path: str, output_dir: str) -> str:
    """
    Extracts the `Saved Places.json` file from a Google Takeout zip archive.

    Args:
        zip_path (str): Path to the Google Takeout ZIP file.
        output_dir (str): Directory to extract the contents to.

    Returns:
        str: Absolute path to the extracted `Saved Places.json` file.

    Raises:
        FileNotFoundError: If `Saved Places.json` is not found in the archive.
    """
    zip_path: Path = Path(zip_path)
    output_dir: Path = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Extracting zip file: {zip}", zip=str(zip_path))
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(output_dir)

    # Search for the GeoJSON file
    logger.info("Searching for 'Saved Places.json' in {dir}", dir=str(output_dir))
    for path in output_dir.rglob("Saved Places.json"):
        logger.success("Found Saved Places.json at {path}", path=str(path))
        return str(path)

    error_msg = "Saved Places.json not found in the provided ZIP file."
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)


def load_geojson(json_path: str) -> dict:
    """
    Loads a GeoJSON file into a Python dictionary.

    Args:
        json_path (str): Path to the GeoJSON file.

    Returns:
        dict: Parsed GeoJSON content.
    """
    json_path: Path = Path(json_path)
    logger.info("Loading GeoJSON file: {path}", path=str(json_path))
    with json_path.open("r", encoding="utf-8") as f:
        data: dict = json.load(f)
    logger.success(
        "Loaded GeoJSON with {count} features.", count=len(data.get("features", []))
    )
    return data
