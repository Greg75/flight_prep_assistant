import logging
import os
import re
import sys
import time
from datetime import datetime
from enum import Enum, IntEnum
from functools import wraps
from http.client import HTTPException
from pathlib import Path
from typing import Dict, List, Literal, Optional, Self
from uuid import UUID, uuid4

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from jinja2 import Environment, FileSystemLoader, TemplateError
from math import sin
from pydantic import BaseModel, Field
from starlette.requests import Request
from weasyprint import HTML

load_dotenv()

# Creating a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Creating a console and file handlers
console_handler = logging.StreamHandler(stream=sys.stdout)
file_handler = logging.FileHandler(filename="flight_prep_assistant.log", encoding="utf-8")

# Setting logging levels
console_handler.setLevel(logging.INFO)
file_handler.setLevel(logging.ERROR)

# Define a formatter
formatter = logging.Formatter(
    fmt="%(levelname)s: %(name)s - %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Apply formatter to both console and file handlers
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


# Models classes
class RunwayModel(BaseModel):
    """
    Represents a runway at an airfield.

    Attributes:
        direction (str | None): The runway's direction identifier (e.g., "09/27").
        length (str | None): The total length of the runway, in feet.
        width (str): The width of the runway, in feet.
        surface (str): The surface type of the runway (e.g., asphalt, grass).
    """

    direction: Optional[str] = Field(
        default=None,
        pattern=r"^\d{2,3}|\d{2}[L|R]/\d{2,3}|\d{2}[L|R]$",
        description="The runway's direction identifier.",
    )
    length: Optional[str] = Field(
        default=None,
        pattern=r"^\d{3,5}$",
        description="The total length of the runway in feet.",
    )
    width: Optional[str] = Field(
        default=None, pattern=r"^\d{2,3}$", description="The width of the runway."
    )
    surface: Optional[str] = Field(
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

    direction: Optional[int | str] = Field(
        default=None,
        description="Direction from which wind is blowing or descriptive text.",
    )
    speed: Optional[float] = Field(default=None, description="Wind speed in knots.")


class FrequencyModel(BaseModel):
    """
    Represents communication frequencies for an airfield.

    Attributes:
        twr (str): Tower frequency.
    """

    twr: Optional[str] = Field(default=None, description="Tower frequency.")

    model_config = {"extra": "allow"}


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

    icaoId: Optional[str] = Field(
        default=None, description="The ICAO identifier of the airfield."
    )
    runway: List[RunwayModel] = Field(description="A list of runways at the airfield.")
    elevation: Optional[int] = Field(
        default=None, description="Elevation of the airfield above the sea level."
    )
    wind: WindModel = Field(description="Current wind conditions, direction and speed.")
    temperature: Optional[float] = Field(
        default=None,
        description="Current temperature at the airfield in degrees Celsius.",
    )
    frequency: FrequencyModel = Field(
        description="Communication frequencies for the airfield."
    )
    metar: Optional[str] = Field(
        default=None, description="The latest METAR weather report for the airfield."
    )
    taf: Optional[str] = Field(
        default=None, description="The latest TAF report for the airfield."
    )


class AircraftModel(BaseModel):
    """
    Represents performance characteristics of an aircraft.

    Attributes:
        type (str): Aircraft type or model name.
        mtow (int): Maximum takeoff weight in kilograms or pounds.
        takeoff_distance_at_sea_level (int): Required takeoff distance at sea level under standard conditions [m / ft].
        landing_distance_at_sea_level (int): Required landing distance at sea level under standard conditions [m / ft].
        stall_speed (int): Stall speed of the aircraft in knots.
        xwind_max_speed (float): Maximum crosswind speed the aircraft can handle, in knots.
    """

    type: str = Field(min_length=3, description="Aircraft type or model name.")
    mtow: int = Field(description="Maximum takeoff weight in kilograms or pounds.")
    takeoff_distance_at_sea_level: int = Field(
        description="Required takeoff distance at sea level under standard conditions."
    )
    landing_distance_at_sea_level: int = Field(
        description="Required landing distance at sea level under standard conditions."
    )
    stall_speed: int = Field(description="Stall speed of the aircraft in knots.")
    xwind_max_speed: float = Field(
        description="Maximum crosswinds speed the aircraft can handle, in knots."
    )


class BriefingModel(BaseModel):
    """
    Represents a comprehensive preflight briefing for a pilot.

    This model includes key data about the aircraft, departure and arrival airfields,
    and a recommendation based on current flight conditions (e.g., weather, suitability).

    Attributes:
        briefing_id (UUID): Unique briefing id.
        aircraft (AircraftModel): Information about the aircraft used for the flight.
        departure_airfield (AirfieldModel): Data about the departure airfield, including weather.
        arrival_airfield (AirfieldModel): Data about the arrival airfield, including weather.
        recommendation (Literal["NO GO", "GO IFR", "GO VFR"]): Flight recommendation based on the briefing.
            - "NO GO": Flight is not recommended.
            - "GO IFR": Flight is recommended under Instrument Flight Rules.
            - "GO VFR": Flight is suitable under Visual Flight Rules.
    """

    briefing_id: UUID = Field(default_factory=uuid4, description="Unique briefing ID.")
    aircraft: AircraftModel = Field(
        description="Information about the aircraft used for the flight."
    )
    departure_airfield: AirfieldModel = Field(
        description="Data about the departure airfield including weather."
    )
    arrival_airfield: AirfieldModel = Field(
        description="Data about the arrival airfield including weather."
    )
    recommendation: Literal["NO GO", "GO IFR", "GO VFR"] = Field(
        default="NO GO",
        description="Flight recommendation based on the briefing."
    )


class BriefingStatus(IntEnum):
    """
    Enum representing the various states of a briefing process.

    Attributes:
        PENDING: Represents a briefing that is yet to start.
        IN_PROGRESS: Represents a briefing that is currently underway.
        COMPLETE: Represents a briefing that has been successfully finished.
        ERROR: Represents a briefing that encountered an error during processing.
    """

    PENDING = 1
    IN_PROGRESS = 2
    COMPLETE = 3
    ERROR = -1


class InputData(BaseModel):
    """
    Represents input data required for flight planning.

    Attributes:
        departure_airfield (str): The ICAO code of the departure airfield. Must be exactly 4 alphabetical characters.
        arrival_airfield (str): The ICAO code of the arrival airfield. Must be exactly 4 alphabetical characters.
        aircraft_data (str): The aircraft type identifier. Must be at least 4 characters long.
    """

    departure_airfield: str = Field(
        min_length=4,
        max_length=4,
        pattern=r"^[A-Za-z]{4}$",
        description="The ICAO code of the departure airfield.",
    )
    arrival_airfield: str = Field(
        min_length=4,
        max_length=4,
        pattern=r"^[A-Za-z]{4}$",
        description="The ICAO code of the arrival airfield.",
    )
    aircraft_data: AircraftModel = Field(
        description="The aircraft data collected according to the AircraftModel structure."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "departure_airfield": "EPKK",
                    "arrival_airfield": "EPWR",
                    "aircraft_data": {
                        "type": "3XTrim",
                        "mtow": 495,
                        "takeoff_distance_at_sea_level": 450,
                        "landing_distance_at_sea_level": 250,
                        "stall_speed": 65,
                        "xwind_max_speed": 12,
                    },
                }
            ]
        }
    }


class OpsCalculatorInputData(BaseModel):
    aircraft_data: AircraftModel = Field(description="")
    airfield_data: AirfieldModel = Field(description="")


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

    ids: str = Field(description="The ICAO identifier of the airfield to query.")
    taf: str = Field(default="true", description="Weather to include TAF.")


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


# Helper functions
def get_time(func):
    """
    Decorator that measures and logs the execution time of the decorated function.

    Uses high-resolution timer (`time.perf_counter_ns`) to calculate elapsed time
    in seconds with nanosecond precision. The timing result is logged using the `logger`.

    Args:
        func (Callable): The function to wrap and time.

    Returns:
        Callable: The wrapped function with execution time logging.

    Example:
        @get_time
        def compute():
            # some expensive operation
            pass
    """
    @wraps(func)
    def inner(*args, **kwargs):
        start_time = time.perf_counter_ns()
        logger.info(f"[Timing] Started '{func.__name__}' at {start_time} ns.")
        result = func(*args, **kwargs)
        elapsed_ns = time.perf_counter_ns() - start_time
        elapsed_sec = elapsed_ns * 1e-9
        logger.info(f"[Timing] Completed '{func.__name__}' | Duration: {elapsed_sec:.6f} s ({elapsed_ns} ns).")
        return result
    return inner


def convert_to_int(runways_direction: list) -> set[int]:
    """
    Convert a list of runway direction strings into a set of integers.

    Each item in the input list is expected to contain a runway direction
    string (e.g., "07R", "25L/07R", or "18"), possibly including letters or
    slashes. The function extracts the first numeric portion of each
    direction and converts it into an integer (automatically removing
    leading zeros).

    Example:
        >>> convert_to_int(["07R", "25L/07R", "18"])
        {7, 25, 18}

    Args:
        runways_direction (list): A list of runway direction strings.

    Returns:
        set[int]: A set of unique integers representing runway directions.

    Logs:
        Info-level log containing the resulting set of converted integers.
    """
    runways_direction_converted_to_int = {
        int(re.findall(
            pattern=r"\d+",
            string=runway_direction.split('/')[0]
        )[0]) for runway_direction in runways_direction
    }
    logger.info(
        f"Runways extracted from OpsCalculator, converted to integers: "
        f"{runways_direction_converted_to_int}"
    )

    return runways_direction_converted_to_int


def is_within_limits():
    pass


# Base classes
class AircraftOpsCalculator:
    def __init__(self, aircraft_data: AircraftModel, airfield_data: AirfieldModel) -> None:
        self.aircraft_data = aircraft_data.model_dump()
        self.airfield_data = airfield_data.model_dump()
        self.wind = self.airfield_data.get("wind")

    def get_wind_data(self) -> tuple:
        wind_speed = self.wind.get("speed")
        wind_direction = self.wind.get("direction")

        return wind_speed, wind_direction

    def get_runways_direction(self) -> list[str]:
        runways = self.airfield_data.get("runway")
        try:
            runways_direction = [runway.get("direction") for runway in runways]
            logger.info(f"Runways extracted from OpsCalculator: {runways_direction}")

            return runways_direction

        except KeyError as err:
            logger.error(f"Failed to get runways directions | Error: {err}.")
            raise RuntimeError(f"Failed to get runways directions. Check runways data format.") from err

    def calculate_xwind_speed(self):
        pass

    def calculate_xwind_direction(self):
        pass

    def calculate_takeoff_distance(self):
        pass

    def calculate_landing_distance(self):
        pass

    def calculate_density_altitude(self):
        pass


class Briefing:
    """
    Handles the rendering and PDF generation of a flight briefing.

    This class accepts a BriefingModel object, extracts key details, renders an HTML
    representation of the briefing using a Jinja2 template, and generates a PDF file.
    """

    def __init__(self, briefing_model: BriefingModel) -> None:
        """
        Initialize the Briefing instance with a BriefingModel.

        Args:
            briefing_model (BriefingModel): An instance containing briefing data.
        """
        try:
            self.briefing = briefing_model
            self.aircraft = briefing_model.aircraft.model_dump()
            self.departure = briefing_model.departure_airfield.model_dump()
            self.arrival = briefing_model.arrival_airfield.model_dump()
            self.recommendation = briefing_model.recommendation
            self.html: Optional[HTML] = None
        except AttributeError as err:
            logger.error(f"Unable to initialize Briefing. Incomplete BriefingModel | Error: {err}")

    def render_briefing_html(self) -> HTML:
        """
        Render the briefing data into HTML using a Jinja2 template.

        Returns:
            HTML: A WeasyPrint HTML object containing the rendered briefing.
        """
        template_dir = Path(__file__).parent
        environment = Environment(loader=FileSystemLoader(template_dir))

        try:
            template = environment.get_template("briefing.html")
            html_output = template.render(
                departure=self.departure,
                arrival=self.arrival,
                aircraft=self.aircraft,
                recommendation=self.recommendation,
            )

            self.html = HTML(string=html_output)
            return self.html

        except AttributeError as err:
            logger.error(f"Failed to render briefing HTML | Error: {err}")
            raise RuntimeError("Failed to render briefing HTML. Check data structure.") from err

        except TemplateError as err:
            logger.error(f"Failed to render briefing HTML | Error: {err}")
            raise RuntimeError("Failed to render briefing HTML. Check template structure.") from err

    def write_briefing_pdf(self) -> str:
        """
        Write the rendered HTML briefing to a PDF file.

        The filename is constructed using the departure and arrival ICAO codes
        and the current date (e.g., Flight_Briefing_KJFK_to_EGLL_2025-06-04.pdf).

        Returns:
            Path: The file path of the generated PDF.
        """
        if self.html is None:
            raise ValueError(
                "HTML content is not rendered. Call render_briefing_html() first."
            )

        dep_icao = self.departure.get("icaoId", None)
        arr_icao = self.arrival.get("icaoId", None)
        date_str = datetime.today().date().isoformat()
        output_filename = f"Flight_Briefing_{dep_icao}_to_{arr_icao}_{date_str}.pdf"
        output_path = Path.cwd() / output_filename

        self.html.write_pdf(str(output_path))
        return str(output_path)


class ApiUrlKey(str, Enum):
    """
    Enumeration of environment variable keys that store base URLs for different external APIs.

    Members:
        AIRFIELD (str): Environment variable key for the Airfield API base URL.
        WEATHER (str): Environment variable key for the Weather API base URL.
        NOTAM (str): Environment variable key for the NOTAM API base URL.
        AIRCRAFT (str): Environment variable key for the Aircraft API base URL.
    """

    AIRFIELD = "AIRFIELD_API_URL"
    WEATHER = "WEATHER_API_URL"
    NOTAM = "NOTAM_API_URL"
    AIRCRAFT = "AIRCRAFT_API_URL"


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


class AirfieldModelBuilder:
    """
    A builder class for constructing `AirfieldModel` instances by aggregating data
    from multiple API sources, such as airfield and weather data.
    """

    def __init__(self) -> None:
        """
        Initializes the builder with an empty airfield records dictionary.
        """
        self.airfield_records = {}

    def add_airfield_data(
        self, airfield_api: ApiClient, params: AirfieldParams
    ) -> Self:
        """
        Loads airfield data from the provided API and updates internal records.

        Args:
            airfield_api: An API interface with a `load_data(params)` method.
            params: Parameters to be passed to the `load_data` method.

        Returns:
            Self: Returns the builder instance for method chaining.
        """
        self.airfield_records.update(
            {
                k: v
                for record in airfield_api.load_data(params)
                for k, v in record.items()
            }
        )
        return self

    def add_weather_data(self, weather_api: ApiClient, params: AirfieldParams) -> Self:
        """
        Loads weather data from the provided API and updates internal records.

        Args:
            weather_api: An API interface with a `load_data(params)` method.
            params: Parameters to be passed to the `load_data` method.

        Returns:
            Self: Returns the builder instance for method chaining.
        """
        self.airfield_records.update(
            {
                k: v
                for record in weather_api.load_data(params)
                for k, v in record.items()
            }
        )
        return self

    def build(self) -> AirfieldModel | None:
        """
        Builds and returns a list containing a single `AirfieldModel` instance
        using the accumulated data.

        Returns:
            AirfieldModel | None: An AirfieldModel instance, or None if data is insufficient.
        """
        if not self.airfield_records.get("icaoId"):
            return None
        else:
            runways = self.airfield_records.get("runways", [])
            frequencies = self.airfield_records.get("freqs")
            parsed_frequencies = self._extract_frequencies(frequencies)

            return AirfieldModel(
                icaoId=self.airfield_records.get("icaoId", None),
                runway=[
                    RunwayModel(
                        direction=runway.get("id", None),
                        length=runway.get("dimension", None).split("x")[0],
                        width=runway.get("dimension", None).split("x")[1],
                        surface=runway.get("surface", None),
                    ).model_dump()
                    for runway in runways
                ],
                elevation=self.airfield_records.get("elev", None),
                wind=WindModel(
                    direction=self.airfield_records.get("wdir", None),
                    speed=self.airfield_records.get("wspd", None),
                ),
                temperature=self.airfield_records.get("temp", None),
                frequency=parsed_frequencies,
                metar=self.airfield_records.get("rawOb", None),
                taf=self.airfield_records.get("rawTaf", None),
            )

    @staticmethod
    def _extract_runways(runways_input: list) -> list[RunwayModel]:
        """
        Converts a list of raw runway data into a list of serialized `RunwayModel` instances.

        Args:
            runways_input (list): A list of dictionaries containing runway information.

        Returns:
            list: A list of serialized RunwayModel data (as dicts).
        """
        if runways_input:
            return [
                RunwayModel(
                    direction=runway_from_api.get("id"),
                    length=runway_from_api.get("dimension").split("x")[0],
                    width=runway_from_api.get("dimension").split("x")[1],
                    surface=runway_from_api.get("surface"),
                ).model_dump()
                for runway_from_api in runways_input
            ]
        else:
            return []

    @staticmethod
    def _extract_frequencies(api_frequencies: str) -> FrequencyModel | dict:
        """
        Parses frequency data from a semicolon-separated string and constructs a `FrequencyModel`.

        Args:
            api_frequencies (str): A string containing frequency pairs in the format "type, value;".

        Returns:
            FrequencyModel: A populated FrequencyModel object or empty dict.
        """
        if api_frequencies:
            return FrequencyModel(
                **{
                    freq.split(",")[0].strip().lower(): freq.split(",")[1].strip()
                    for freq in api_frequencies.split(";")
                    if "," in freq
                }
            )
        else:
            return {}


class BriefingGenerator:
    """
    A class responsible for generating a flight briefing using airfield and weather data.

    This class builds detailed models for both departure and arrival airfields
    by integrating airfield metadata and weather conditions through API clients.
    """

    def __init__(
        self, data: InputData, airfield_api: ApiClient, weather_api: ApiClient
    ) -> None:
        """
        Initialize the BriefingGenerator instance with input data and API clients.

        Args:
            data (InputData): The input parameters including aircraft, departure, and arrival details.
            airfield_api (ApiClient): API client for retrieving airfield information.
            weather_api (ApiClient): API client for retrieving weather data.
        """
        self.data = data
        self.airfield_api = airfield_api
        self.weather_api = weather_api
        self.departure_params = AirfieldParams(ids=self.data.departure_airfield)
        self.arrival_params = AirfieldParams(ids=self.data.arrival_airfield)

    def generate_briefing(self) -> BriefingModel:
        """
        Generate the full flight briefing model.

        This method builds the airfield and weather models for both departure and arrival,
        and constructs the final BriefingModel with a default recommendation.

        Returns:
            BriefingModel: A structured model containing aircraft, airfield, and weather data.
        """
        departure_airfield_model_builder = AirfieldModelBuilder()
        arrival_airfield_model_builder = AirfieldModelBuilder()

        departure_airfield_model_builder.add_airfield_data(
            airfield_api=self.airfield_api, params=self.departure_params
        )
        departure_airfield_model_builder.add_weather_data(
            weather_api=self.weather_api, params=self.departure_params
        )
        arrival_airfield_model_builder.add_airfield_data(
            airfield_api=self.airfield_api, params=self.arrival_params
        )
        arrival_airfield_model_builder.add_weather_data(
            weather_api=self.weather_api, params=self.arrival_params
        )

        departure_airfield_ops_calculator = AircraftOpsCalculator(
            aircraft_data=self.data.aircraft_data,
            airfield_data=departure_airfield_model_builder.build())
        convert_to_int(departure_airfield_ops_calculator.get_runways_direction())
        logger.info(f"Departure airfield wind parameters: {departure_airfield_ops_calculator.get_wind_data()}")
        logger.info(f"Departure airfield crosswind speed: {departure_airfield_ops_calculator.calculate_xwind_speed()}")

        arrival_airfield_ops_calculator = AircraftOpsCalculator(
            aircraft_data=self.data.aircraft_data,
            airfield_data=arrival_airfield_model_builder.build())
        convert_to_int(arrival_airfield_ops_calculator.get_runways_direction())
        logger.info(f"Arrival airfield wind parameters: {arrival_airfield_ops_calculator.get_wind_data()}")
        logger.info(f"Arrival airfield crosswind speed: {arrival_airfield_ops_calculator.calculate_xwind_speed()}")

        return BriefingModel(
            aircraft=self.data.aircraft_data,
            departure_airfield=departure_airfield_model_builder.build(),
            arrival_airfield=arrival_airfield_model_builder.build(),
        )


def create_airfield_model(
    airfield_api: ApiClient, weather_api: ApiClient, airfield_api_params: AirfieldParams
) -> AirfieldModel:
    """
    Build an AirfieldModel using the given API clients and parameters.

    Args:
        airfield_api (ApiClient): API client for accessing airfield data.
        weather_api (ApiClient): API client for accessing weather data.
        airfield_api_params (AirfieldParams): Parameters specifying the airfield data to retrieve.

    Returns:
        AirfieldModel: A model combining both airfield and weather data for the specified location.
    """
    airfield_model_builder = AirfieldModelBuilder()
    airfield_model_builder.add_airfield_data(
        airfield_api=airfield_api, params=airfield_api_params
    )
    airfield_model_builder.add_weather_data(
        weather_api=weather_api, params=airfield_api_params
    )

    airfield_model = airfield_model_builder.build()

    return airfield_model


def create_briefing(briefing_model: BriefingModel) -> Briefing:
    """
    Generate an HTML representation of the flight briefing from the briefing model.

    Args:
        briefing_model (BriefingModel): The model containing the full flight briefing information.

    Returns:
        Briefing: An object capable of rendering the briefing as HTML.
    """
    return Briefing(briefing_model=briefing_model)


app = FastAPI(debug=True)

briefing_store: Dict[str, BriefingModel] = {}
briefing_status: Dict[str, BriefingStatus] = {}


@app.get(
    path="/",
    summary="Root endpoint for Briefing API",
    description="This is the root endpoint of the Briefing API. It simply returns a message indicating "
    "that the API is running and operational.",
)
def root() -> dict:
    """
    Root endpoint for the Briefing API.

    Returns:
        dict: A simple message indicating that the API is running.
    """
    logger.info("Root endpoint accessed: Briefing API is running")
    return {"message": "Briefing API is running."}


@app.get(
    path="/ping",
    summary="Ping the API to check its health",
    description="This endpoint returns a status message indicating that the API is healthy and responsive. "
    "It's often used to check if the API is up and running.",
)
def ping_api() -> dict:
    """
    Health check endpoint to verify the API is responsive.

    Returns:
        dict: A status message indicating the API is healthy.
    """
    logger.info("Health check ping received: API is responsive")
    return {"status": "healthy"}


@app.post(
    path="/generate",
    response_model=BriefingModel,
    summary="Generate a flight briefing based on input data",
    description="This endpoint generates a flight briefing based on the provided input data, "
    "including details like departure and arrival airfields. It returns a structured "
    "BriefingModel containing all briefing information for the flight.",
)
def generate_briefing(data: InputData) -> BriefingModel:
    """
    Generate a flight briefing based on the provided input data.

    This function initializes API clients, invokes the briefing generation logic,
    stores the result, and returns a structured briefing model.

    Args:
        data (InputData): Input parameters including departure, arrival, and other flight-related details.

    Returns:
        BriefingModel: A structured object containing the generated flight briefing.
    """
    try:
        briefing = BriefingGenerator(
            data=data,
            airfield_api=ApiClient(api_url_key=ApiUrlKey.AIRFIELD),
            weather_api=ApiClient(api_url_key=ApiUrlKey.WEATHER),
        ).generate_briefing()

    except HTTPException as exp:
        logger.warning(f"Briefing generation failed due to HTTP error | Details: {exp}")
        raise RuntimeError("Unable to generate briefing")

    except Exception as exp:
        logger.error(msg=f"Unexpected error during briefing generation | Error: {exp}", exc_info=True)
        raise RuntimeError("Unexpected error during briefing generation")

    else:
        briefing_id = str(briefing.briefing_id)
        logger.info(f"Briefing generated successfully | ID: {briefing_id}")

        briefing_store.update({briefing_id: briefing})
        logger.info(f"Briefing saved to in-memory store | ID: {briefing_id}")

        return briefing


@app.get(
    path="/briefing/{briefing_id}/download",
    response_class=FileResponse,
    summary="Download a briefing as a PDF",
    description="This endpoint allows you to download a generated flight briefing as a PDF "
    "using the provided briefing ID. If the briefing ID is invalid, a 404 error will be returned. "
    "If there are issues during PDF generation, a 500 error will be raised.",
)
@get_time
def download_briefing(request: Request, briefing_id: str) -> FileResponse:
    """
    Downloads the PDF version of a generated flight briefing.

    Args:
        request (Request): .
        briefing_id (str): The ID of the briefing to download.

    Returns:
        Path: The file path to the generated PDF.

    Raises:
        HTTPException: If the briefing ID is not found or PDF generation fails.
    """
    # Dummy request
    _ = request.client.host

    try:
        briefing_model = briefing_store.get(briefing_id)
    except KeyError as err:
        logger.error(f"Failed to retrieve briefing model | ID: {briefing_id} | Error: {err}")
        raise RuntimeError(f"Invalid key. Unable to fetch the briefing model | Error: {err}")
    else:
        # Update and log status: PENDING
        briefing_status.update({briefing_id: BriefingStatus.PENDING})
        logger.info(f"Briefing download requested | ID: {briefing_id} | Status: PENDING")

        time.sleep(10)

        # Update and log status: IN_PROGRESS
        briefing_status.update({briefing_id: BriefingStatus.IN_PROGRESS})
        logger.info(f"Briefing rendering started | ID: {briefing_id} | Status: IN_PROGRESS")

        briefing = Briefing(briefing_model)
        briefing.render_briefing_html()

        time.sleep(10)

        # Update and log status: COMPLETE
        briefing_status.update({briefing_id: BriefingStatus.COMPLETE})
        logger.info(f"Briefing generation complete | ID: {briefing_id} | Status: COMPLETE")

        return FileResponse(briefing.write_briefing_pdf())


@app.get(
    path="/briefing/{briefing_id}/status",
    summary="Check the status of a briefing",
    description="This endpoint allows you to retrieve the current status of a briefing by providing "
    "the briefing ID. If the briefing ID exists, it returns the corresponding status. "
    "If the briefing ID is invalid, the status will be `None` or an error.",
)
def check_status(briefing_id: str) -> dict:
    """
    Check the current status of a briefing.

    Args:
        briefing_id (str): The unique identifier of the briefing.

    Returns:
        dict: A dictionary containing the briefing ID and its current status.
    """
    try:
        status = briefing_status.get(briefing_id)
    except KeyError as err:
        logger.error(f"Failed to retrieve status for briefing ID '{briefing_id}': {err}")
        raise RuntimeError(f"Invalid key. Unable to fetch the briefing status | Error: {err}")
    else:
        logger.info(
            f"Briefing status retrieved | ID: {briefing_id} | Current Status: {status}"
        )

        return {briefing_id: status}


if __name__ == "__main__":
    uvicorn.run(app="main:app", host="127.0.0.1", port=8000)
