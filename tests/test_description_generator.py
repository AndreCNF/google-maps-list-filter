import pytest
from pydantic import ValidationError
from google_maps_list_filter.description_generator import (
    generate_place_description,
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


@pytest.mark.parametrize(
    "input_data, error_field",
    [
        ({}, "title"),
        ({"title": "A", "categories": [], "description": "Desc"}, "categories"),
        ({"title": "A", "categories": ["cat"]}, "description"),
    ],
)
def test_place_description_model_invalid(input_data, error_field):
    """
    Test that the PlaceDescription model raises ValidationError for missing fields.
    """
    with pytest.raises(ValidationError) as exc_info:
        PlaceDescription(**input_data)
    errors = exc_info.value.errors()
    assert any(error["loc"][0] == error_field for error in errors)


def test_generate_place_description_api_error(monkeypatch):
    """
    Test that generate_place_description raises Exception when OpenAI API errors.
    """

    def mock_parse(*args, **kwargs):
        raise Exception("API failure")

    monkeypatch.setattr(
        "google_maps_list_filter.description_generator.openai.Client.beta.chat.completions.parse",
        mock_parse,
    )
    with pytest.raises(Exception) as exc_info:
        generate_place_description("Place", ["cat"], "key")
    assert str(exc_info.value) == "API failure"
