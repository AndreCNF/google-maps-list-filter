import pytest
from google_maps_list_filter.description_generator import (
    PlaceDescription,
)


def test_place_description_model_valid():
    """
    Test that the PlaceDescription model accepts valid data.
    """
    data = {
        "title": "Central Park",
        "categories": ["park", "tourist_attraction"],
        "description": "A large public park in New York City.",
    }
    model = PlaceDescription(**data)
    assert model.title == data["title"]
    assert model.categories == data["categories"]
    assert model.description == data["description"]
