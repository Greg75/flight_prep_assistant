import re
from typing import Self

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, ValidationInfo


class RunwayModel(BaseModel):
    """
    Represents a runway at an airfield.

    Attributes:
        direction (set[int] | None): The runway's direction identifier (e.g., "09/27").
        length (int | None): The total length of the runway, in feet.
        width (int | None): The width of the runway, in feet.
        surface (str | None): The surface type of the runway (e.g., asphalt, grass).
    """

    direction: list[int] | None = Field(
        default=None,
        description="The runway's direction.",
    )
    length: int | None = Field(
        default=None,
        description="The total length of the runway in feet.",
    )
    width: int | None = Field(
        default=None,
        description="The width of the runway."
    )
    surface: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z]{1,99}$",
        description="The surface type of the runway.",
    )

    @field_validator("direction", mode="before")
    @classmethod
    def validate_direction(cls, value: list) -> list | None:
        """
        Normalize and convert runway direction strings (like '09/27', '09L/27R') into a set of ints {9, 27}.
        """
        if value is None:
            return None

        pattern = re.compile(r"\d{2}")

        # If already a list of ints, return as-is
        if isinstance(value, list) and all(isinstance(v, int) for v in value):
            return value

        # Convert list of strings or mixed values into one string
        if isinstance(value, list):
            joined = "".join(map(str, value))
            matches = pattern.findall(joined)
            return [int(m) for m in matches]

        # Handle plain string input (e.g., "09/27" or "09L/27R")
        if isinstance(value, str):
            matches = pattern.findall(value)
            return [int(m) for m in matches]

        raise TypeError(f"Unexpected type for runway direction: {type(value)}.")

    @field_validator("length", "width", mode="before")
    @classmethod
    def validate_length(cls, value: str, info: ValidationInfo) -> int | None:
        if value is None:
            return None

        if isinstance(value, str):
            cleaned = re.sub(r"\D", "", value)
            if not cleaned:
                raise ValueError(f"No numeric data found for {info.field_name}: {value!r}")
            return int(cleaned)

        if isinstance(value, int):
            return value

        raise TypeError(f"Unexpected type of the runway {info.field_name}: {type(value).__name__}.")

    @field_validator("surface")
    @classmethod
    def validate_surface(cls, value: str | None) -> str | None:
        return value.lower() if value else None


class WindModel(BaseModel):
    """
    Represents wind conditions at an airfield.

    Attributes:
        direction (int | str | None): The wind direction in degrees, or descriptive text.
        speed (float | None): The wind speed in knots or meters per second.
    """

    model_config = ConfigDict(strict=True)

    direction: int | str = Field(
        description="Direction from which wind is blowing or descriptive text.",
    )
    speed: int = Field(ge=0, description="Wind speed in knots.")
    gust: int | None = Field(default=None, description="Wind gusts in knots.")

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: int | str) -> int:
        if isinstance(value, bool):
            raise TypeError(f"Invalid data type of wind direction: {value}.")

        if not isinstance(value, int) and not isinstance(value, str):
            raise TypeError(f"Invalid data type of wind direction: {value}.")

        if isinstance(value, str):
            if value.upper() in {"VRB", "CALM", "VAR", ""}:
                return 0
            if value.isdigit():
                return int(value) % 360
            raise ValueError(f"Invalid wind direction: {value}.")

        return value % 360

    @model_validator(mode="after")
    def validate_gust_vs_speed(self) -> Self:
        if self.gust is not None and self.gust < self.speed:
            raise ValueError("Wind gust must be greater than wind speed.")

        return self


class FrequencyModel(BaseModel):
    """
    Represents communication frequencies for an airfield.

    Attributes:
        twr (str): Tower frequency.
    """
    model_config = ConfigDict(extra="allow")

    twr: str | None = Field(default=None, description="Tower frequency.")

    @field_validator("twr")
    @classmethod
    def validate_twr_freq(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()

        raise ValueError(f"Invalid data type for TWR frequency field: {value}")

    @model_validator(mode="before")
    @classmethod
    def strip_all_model_fields(cls, fields: dict) -> dict:
        stripped_fields = {}
        for key, value in fields.items():
            if isinstance(value, str):
                stripped_fields.update({key: value.strip()})
            else:
                stripped_fields.update({key: value})

        return stripped_fields


class AirfieldModel(BaseModel):
    """
    Represents an airfield including its runways, weather, and communication data.

    Attributes:
        icaoId (str): The ICAO identifier for the airfield.
        runway (List[RunwayModel]): A list of runways at the airfield.
        elevation (int | None): Elevation of the airfield above sea level in feet.
        wind (WindModel): Current wind conditions.
        temperature (float | None): Current temperature at the airfield in degrees Celsius.
        frequency (FrequencyModel): Communication frequencies for the airfield.
        metar (str | None): The latest METAR weather report for the airfield.
        taf (str | None): The latest TAF weather report for the airfield.
    """

    icaoId: str | None = Field(
        default=None, description="The ICAO identifier of the airfield."
    )
    runway: list[RunwayModel] = Field(description="A list of runways at the airfield.")
    elevation: int | None = Field(
        default=None, description="Elevation of the airfield above the sea level."
    )
    wind: WindModel = Field(description="Current wind conditions, direction and speed.")
    temperature: float | None = Field(
        default=None,
        ge=-80,
        le=60,
        description="Current temperature at the airfield in degrees Celsius.",
    )
    frequency: FrequencyModel = Field(
        description="Communication frequencies for the airfield."
    )
    metar: str | None = Field(
        default=None, description="The latest METAR weather report for the airfield."
    )
    taf: str | None = Field(
        default=None, description="The latest TAF report for the airfield."
    )

    @field_validator("icaoId")
    @classmethod
    def validate_icao(cls, value: str) -> str:
        if not value:
            raise ValueError("ICAO code cannot be empty.")

        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z]{4}", value):
            raise ValueError(f"Invalid ICAO code: {value}. Expected 4-letter ICAO airfield code identifier.")
        return value

    @field_validator("runway")
    @classmethod
    def validate_runway(cls, value: list[RunwayModel]) -> list[RunwayModel]:
        if not value:
            raise ValueError("Airfield must include at least one runway.")
        return value

    @field_validator("elevation")
    @classmethod
    def validate_elevation(cls, value: int | None) -> int | None:
        if value is not None and not (-1000 <= value <= 15000):
            raise ValueError("Elevation must be between -1000 and 15000 ft.")
        return value

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, value: float | None) -> float | None:
        return round(value, 1) if value is not None else None
