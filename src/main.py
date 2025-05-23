import os
import requests
from enum import Enum
from dotenv import load_dotenv
from requests import Response
from pydantic import BaseModel, Field
from typing import List, Self

load_dotenv()


# Helper classes and functions
class RunwayModel(BaseModel):
    """
    Represents a runway at an airfield.

    Attributes:
        direction (str | None): The runway's direction identifier (e.g., "09/27").
        length (str | None): The total length of the runway, typically in meters or feet.
        width (str): The width of the runway, typically in meters or feet.
        surface (str): The surface type of the runway (e.g., asphalt, grass).
        tora (int): Takeoff Run Available — the length of runway declared available and suitable for the ground run of an aircraft taking off.
        lda (int): Landing Distance Available — the length of runway declared suitable for landing.
    """
    direction: str | None
    length: str | None
    width: str
    surface: str
    tora: int
    lda: int


class WindModel(BaseModel):
    """
    Represents wind conditions at an airfield.

    Attributes:
        direction (int | str | None): The wind direction in degrees, or descriptive text.
        speed (float | None): The wind speed in knots or meters per second.
    """
    direction: int | str | None
    speed: float | None


class FrequencyModel(BaseModel):
    """
    Represents communication frequencies for an airfield.

    Attributes:
        atis (str): Automatic Terminal Information Service frequency.
        twr (str): Tower frequency.
    """
    atis: str = None
    twr: str = None


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
    """
    icaoId: str
    runway: List[RunwayModel]
    elevation: int | None
    wind: WindModel
    temperature: float | None
    frequency: FrequencyModel
    metar: str | None


class AircraftModel(BaseModel):
    """
    Represents performance characteristics of an aircraft.

    Attributes:
        type (str): Aircraft type or model name.
        mtow (int): Maximum takeoff weight in kilograms or pounds.
        takeoff_distance_at_sea_level (int): Required takeoff distance at sea level under standard conditions, in meters or feet.
        landing_distance_at_sea_level (int): Required landing distance at sea level under standard conditions, in meters or feet.
        stall_speed (int): Stall speed of the aircraft in knots.
        xwind_max_speed (float): Maximum crosswind speed the aircraft can handle, in knots.
    """
    type: str
    mtow: int
    takeoff_distance_at_sea_level: int
    landing_distance_at_sea_level: int
    stall_speed: int
    xwind_max_speed: float


class InputData(BaseModel):
    """
    Represents input data required for flight planning.

    Attributes:
        departure_airfield (str): The ICAO code of the departure airfield. Must be exactly 4 alphabetical characters.
        arrival_airfield (str): The ICAO code of the arrival airfield. Must be exactly 4 alphabetical characters.
        aircraft_data (str): The aircraft type identifier. Must be at least 4 characters long.
    """
    departure_airfield: str = Field(min_length=4, max_length=4, pattern=r'^[A-Za-z]{4}$')
    arrival_airfield: str = Field(min_length=4, max_length=4, pattern=r'^[A-Za-z]{4}$')
    aircraft_data: AircraftModel = Field()


def get_input() -> InputData:
    """
    Prompts the user to enter flight planning data via standard input.

    Returns:
        InputData: A validated instance containing the departure airfield, arrival airfield, and aircraft type.

    Notes:
        - ICAO codes are automatically converted to uppercase.
        - Raises a ValidationError if the input does not meet the model's constraints.
    """
    departure_airfield = input("Departure airfield ICAO code: ").upper()
    arrival_airfield = input("Arrival airfield ICAO code: ").upper()
    aircraft_data = AircraftModel(
        type=input("Aircraft type: "),
        mtow=int(input(f"Max takeoff weight: ")),
        takeoff_distance_at_sea_level=int(input("Takeoff distance at sea level: ")),
        landing_distance_at_sea_level=int(input("Landing distance at sea level: ")),
        stall_speed=int(input("Stall speed: ")),
        xwind_max_speed=float(input("Max crosswind speed: ")),
    )

    return InputData(
        departure_airfield=departure_airfield,
        arrival_airfield=arrival_airfield,
        aircraft_data=aircraft_data,
    )


# Basic classes
class ApiParams(BaseModel):
    """
    Base class for API request parameters.

    Attributes:
        format (str): The desired format of the API response (e.g., "json", "xml").
    """
    format: str


class AirfieldParams(ApiParams):
    """
    Parameters specific to airfield data API requests.

    Attributes:
        ids (str): Comma-separated ICAO identifiers of the airfields to query.
    """
    ids: str


class AirfieldModelBuilder:
    """
    A builder class for constructing `AirfieldModel` instances by aggregating data
    from multiple API sources, such as airfield and weather data.
    """

    def __init__(self):
        """
        Initializes the builder with an empty airfield records dictionary.
        """
        self.airfield_records = {}

    def add_airfield_data(self, airfield_api, params) -> Self:
        """
        Loads airfield data from the provided API and updates internal records.

        Args:
            airfield_api: An API interface with a `load_data(params)` method.
            params: Parameters to be passed to the `load_data` method.

        Returns:
            Self: Returns the builder instance for method chaining.
        """
        self.airfield_records.update({k: v for record in airfield_api.load_data(params) for k, v in record.items()})
        return self

    def add_weather_data(self, weather_api, params) -> Self:
        """
        Loads weather data from the provided API and updates internal records.

        Args:
            weather_api: An API interface with a `load_data(params)` method.
            params: Parameters to be passed to the `load_data` method.

        Returns:
            Self: Returns the builder instance for method chaining.
        """
        self.airfield_records.update({k: v for record in weather_api.load_data(params) for k, v in record.items()})
        return self

    def build(self) -> AirfieldModel | None:
        """
        Builds and returns a list containing a single `AirfieldModel` instance
        using the accumulated data.

        Returns:
            AirfieldModel | None: An AirfieldModel instance, or None if data is insufficient.
        """
        runways = self.airfield_records.get("runways", [])
        frequencies = self.airfield_records.get("freqs")
        parsed_frequencies = self._extract_frequencies(frequencies)

        return AirfieldModel(
            icaoId=self.airfield_records.get("icaoId", "Null"),
            runway=[RunwayModel(
                direction=runway.get("id", "Null"),
                length=runway.get("dimension", "Null").split("x")[0],
                width=runway.get("dimension", "Null").split("x")[1],
                surface=runway.get("surface", "Null"),
                tora=1,
                lda=1,
            ).model_dump()
                    for runway in runways],
            elevation=self.airfield_records.get("elev", None),
            wind=WindModel(
                direction=self.airfield_records.get("wdir", None),
                speed=self.airfield_records.get("wspd", None),
            ),
            temperature=self.airfield_records.get("temp", None),
            frequency=parsed_frequencies,
            metar=self.airfield_records.get("rawOb", None)
        ).model_dump()

    @staticmethod
    def _extract_runways(runways_input: list) -> list:
        """
        Converts a list of raw runway data into a list of serialized `RunwayModel` instances.

        Args:
            runways_input (list): A list of dictionaries containing runway information.

        Returns:
            list: A list of serialized RunwayModel data (as dicts).
        """
        return [RunwayModel(
            direction=runway_from_api.get("id"),
            length=runway_from_api.get("dimension").split("x")[0],
            width=runway_from_api.get("dimension").split("x")[1],
            surface=runway_from_api.get("surface"),
            tora=1,
            lda=1,
        ).model_dump()
                for runway_from_api in runways_input]

    @staticmethod
    def _extract_frequencies(api_frequencies):
        """
        Parses frequency data from a semicolon-separated string and constructs a `FrequencyModel`.

        Args:
            api_frequencies (str): A string containing frequency pairs in the format "type, value;".

        Returns:
            FrequencyModel: A populated FrequencyModel object.
        """
        return FrequencyModel(**{
            freq.split(",")[0].strip().lower(): freq.split(",")[1].strip()
            for freq in api_frequencies.split(";")
            if "," in freq
        })


class AirfieldModelFacade:
    def __init__(self, airfield_api, weather_api):
        self.airfield_api = airfield_api
        self.weather_api = weather_api

    def load_data(self) -> dict:
        airfield_data = self.airfield_api.load_data()
        weather_data = self.weather_api.load_data()
        return {**airfield_data, **weather_data}


class ApiUrlKey(Enum):
    """
    Enumeration of environment variable keys that store base URLs for different external APIs.

    Members:
        AIRFIELD (str): Environment variable key for the Airfield API base URL.
        WEATHER (str): Environment variable key for the Weather API base URL.
        NOTAM (str): Environment variable key for the NOTAM API base URL.
    """
    AIRFIELD = "AIRFIELD_API_URL"
    WEATHER = "WEATHER_API_URL"
    NOTAM = "NOTAM_API_URL"


class ApiClient:
    """
    Generic API client for sending GET requests to a specified external API endpoint.

    This class is intended to be used as a base or utility class for interacting with various APIs.
    The actual base URL is loaded from an environment variable, allowing for secure and flexible configuration.

    Attributes:
        api_url (str): The fully resolved API base URL from an environment variable.
    """

    def __init__(self, api_url_key: ApiUrlKey) -> None:
        """
        Initializes the API client with a base URL resolved from an environment variable.

        Args:
            api_url_key (str): The environment variable key holding the base URL.
        """
        self.api_url = os.getenv(api_url_key.value)

        if not self.api_url:
            raise ValueError(f"Environment variable '{api_url_key}' not set or empty.")

    def load_data(self, params: ApiParams) -> dict:
        """
        Sends a GET request to the configured API endpoint with optional query parameters.

        Args:
            **params: Arbitrary keyword arguments passed as query parameters to the API.

        Returns:
            Response: A `requests.Response` object containing the server's response.

        Raises:
            requests.RequestException: If the HTTP request fails.
        """
        try:
            response = requests.get(url=self.api_url, params=params.model_dump())
            return response.json() if response.status_code == 200 else {}
        except requests.RequestException as exp:
            raise exp


def main():
    airfield_api = ApiClient(api_url_key=ApiUrlKey.AIRFIELD)
    weather_api = ApiClient(api_url_key=ApiUrlKey.WEATHER)

    data_inputs = get_input()

    departure_params = AirfieldParams(
        ids=data_inputs.departure_airfield,
        format="json",
    )

    arrival_params = AirfieldParams(
        ids=data_inputs.arrival_airfield,
        format="json",
    )

    departure_airfield_model_builder = AirfieldModelBuilder()
    arrival_airfield_model_builder = AirfieldModelBuilder()

    departure_airfield_model_builder.add_airfield_data(airfield_api=airfield_api, params=departure_params)
    departure_airfield_model_builder.add_weather_data(weather_api=weather_api, params=departure_params)

    arrival_airfield_model_builder.add_airfield_data(airfield_api=airfield_api, params=arrival_params)
    arrival_airfield_model_builder.add_weather_data(weather_api=weather_api, params=arrival_params)

    print(50 * "-")
    print(f"Departure airfield data: {departure_airfield_model_builder.build()}.")
    print(f"Arrival airfield data: {arrival_airfield_model_builder.build()}.")
    print(50 * "-")


if __name__ == "__main__":
    main()
