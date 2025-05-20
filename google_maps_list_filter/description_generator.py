"""
Module for generating AI-powered descriptions of geocoded places using OpenAI and Pydantic for structured outputs.
"""

import openai
from loguru import logger
from pydantic import BaseModel, Field, ValidationError


class PlaceDescription(BaseModel):
    """
    Pydantic model defining the structured schema for a place description.
    """

    title: str = Field(description="The name or title of the place.")
    categories: list[str] = Field(description="Categories associated with the place.")
    description: str = Field(description="AI-generated brief description of the place.")


def generate_place_description(
    place_title: str,
    categories: list[str],
    openai_api_key: str,
    model: str = "gpt-4o-mini-search-preview",
    system_prompt: str = (
        "You are an assistant that writes concise, informative descriptions of places."
    ),
) -> PlaceDescription:
    """
    Generates a brief description for a place using OpenAI chat completion.

    Args:
        place_title (str): Title of the place.
        categories (list[str]): Categories associated with the place.
        openai_api_key (str): API key for OpenAI.
        model (str): Chat model name to use for completion.
        system_prompt (str): System prompt guiding the assistant.

    Returns:
        PlaceDescription: Parsed structured description of the place.

    Raises:
        ValidationError: If the AI response cannot be validated against the schema.
        Exception: For OpenAI API errors.
    """
    client = openai.Client(api_key=openai_api_key)

    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            web_search_options={"search_context_size": "low"},
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Place name: {place_title}\n"
                        f"Categories: {', '.join(categories)}\n"
                        "Provide a concise description:"
                    ),
                },
            ],
            response_format=PlaceDescription,
        )
        parsed: PlaceDescription = completion.choices[0].message.parsed
        return parsed

    except ValidationError as ve:
        logger.error("Failed to validate OpenAI response: {error}", error=str(ve))
        raise
    except Exception as e:
        logger.error(
            "OpenAI API error for place: {title}, error: {error}",
            title=place_title,
            error=str(e),
        )
        raise
