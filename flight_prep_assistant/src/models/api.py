import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ApiParams(BaseModel):
    """
    The base parameter for API request.

    Attributes:
        format (str): The expected format of the API response (e.g., "json", "xml"). Defaults to "json".
    """

    format: str = Field(
        default="json", description="The expected format of the API response."
    )


class AirfieldParams(ApiParams):
    """
    Parameters specific to airfield data API requests.

    Attributes:
        ids (str): The ICAO identifier of the airfield to query.
        taf (str): Whether to include TAF (Terminal Aerodrome Forecast) data in the response. Defaults to "true".
    """

    ids: str = Field(pattern=r"^[a-zA-Z]{4}$", description="The ICAO identifier of the airfield to query.")
    taf: str = Field(default="true", description="Weather to include TAF.")

    @field_validator("ids")
    @classmethod
    def validate_ids(cls, value):
        return value.upper()

    @field_validator("taf")
    @classmethod
    def validate_taf(cls, value):
        if value not in {"true", "false"}:
            raise ValueError("taf must be 'true' or 'false'")

        return value


class AircraftParams(ApiParams):
    """
    Parameters specific to aircraft data API requests.

    Attributes:
        api_key (str): The API key used for authentication and authorization.
        manufacturer (str): The name of the aircraft manufacturer to filter the results (e.g., "Boeing", "Airbus").
    """

    api_key: str = Field(
        description="The API key used for authentication and authorization."
    )
    manufacturer: str = Field(description="The name of the aircraft manufacturer.")
