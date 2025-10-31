from pydantic import BaseModel, Field, ConfigDict, field_validator


class RunwayModel(BaseModel):
    """
    Represents a runway at an airfield.

    Attributes:
        direction (str | None): The runway's direction identifier (e.g., "09/27").
        length (str | None): The total length of the runway, in feet.
        width (str): The width of the runway, in feet.
        surface (str): The surface type of the runway (e.g., asphalt, grass).
    """

    direction: str | None = Field(
        default=None,
        pattern=r"^\d{2,3}|\d{2}[L|R]/\d{2,3}|\d{2}[L|R]$",
        description="The runway's direction identifier.",
    )
    length: str | None = Field(
        default=None,
        pattern=r"^\d{3,5}$",
        description="The total length of the runway in feet.",
    )
    width: str | None = Field(
        default=None,
        pattern=r"^\d{2,3}$",
        description="The width of the runway."
    )
    surface: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z]{1,99}$",
        description="The surface type of the runway.",
    )


class WindModel(BaseModel):
    """
    Represents wind conditions at an airfield.

    Attributes:
        direction (int | str | None): The wind direction in degrees, or descriptive text.
        speed (float | None): The wind speed in knots or meters per second.
    """

    direction: int | str | None = Field(
        default=None,
        description="Direction from which wind is blowing or descriptive text.",
    )
    speed: float | None = Field(default=None, description="Wind speed in knots.")


class FrequencyModel(BaseModel):
    """
    Represents communication frequencies for an airfield.

    Attributes:
        twr (str): Tower frequency.
    """

    twr: str | None = Field(default=None, description="Tower frequency.")

    model_config = ConfigDict(extra="allow")


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

        from flight_prep_assistant.src.helpers import is_not_valid_icao_code

        value = value.strip().upper()
        if is_not_valid_icao_code(icao=value):
            raise ValueError(f"Invalid ICAO code: {value}. Expected 4-letter ICAO airfield code identifier.")
        return value

    @field_validator("runway")
    @classmethod
    def validate_runway(cls, value: list[RunwayModel]) -> list[RunwayModel]:
        if not value:
            raise ValueError("At least one runway needs to be provided.")
        return value
