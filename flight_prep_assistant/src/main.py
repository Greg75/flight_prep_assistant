import logging
import os
import sys
import time
from datetime import datetime
from enum import Enum
from http.client import HTTPException
from pathlib import Path
from typing import Literal, Optional, Self

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from jinja2 import Environment, FileSystemLoader, TemplateError
from math import sin, cos, radians, exp

from starlette.requests import Request
from weasyprint import HTML

from flight_prep_assistant.src.constants import (GRAVITY_FACTOR,
                                                 KNOTS_FACTOR, HEIGHT_APPROXIMATION, CALIBRATED_TAKEOFF_FACTOR,
                                                 CALIBRATED_LANDING_FACTOR)
from flight_prep_assistant.src.enums import BriefingStatus, StallSpeedFactor
from flight_prep_assistant.src.helpers import (is_not_pydantic_model, convert_to_int,
                                               convert_to_tas, get_time)
from flight_prep_assistant.src.models import AircraftModel, AirfieldModel, BriefingModel, ApiParams, AirfieldParams, \
    RunwayModel, WindModel, FrequencyModel, InputData

load_dotenv()

# --- Creating a logger ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# --- Creating a console and file handlers ---
console_handler = logging.StreamHandler(stream=sys.stdout)
file_handler = logging.FileHandler(filename="flight_prep_assistant.log", encoding="utf-8")

# --- Setting logging levels ---
console_handler.setLevel(logging.INFO)
file_handler.setLevel(logging.ERROR)

# --- Define a formatter ---
formatter = logging.Formatter(
    fmt="%(levelname)s: %(name)s - %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# --- Apply formatter to both console and file handlers ---
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# --- Add handlers to the logger ---
logger.addHandler(console_handler)
logger.addHandler(file_handler)


# --- Base classes ---
class AircraftOpsCalculator:
    """
    A calculator for determining aircraft operational parameters related to wind and runway orientation.

    This class processes aircraft and airfield data to compute crosswind and headwind components
    for all available runways at a given airfield.

    Attributes:
        aircraft_data (dict): Serialized data of the aircraft model.
        airfield_data (dict): Serialized data of the airfield model.
        wind (dict): Dictionary containing wind parameters such as speed and direction.
        runways_direction (list[int]): List of runway directions converted to integers.
    """

    def __init__(self, aircraft_data: AircraftModel, airfield_data: AirfieldModel) -> None:
        """
        Initialize the AircraftOpsCalculator with aircraft and airfield data.

        Args:
            aircraft_data (AircraftModel): Aircraft model object containing aircraft details.
            airfield_data (AirfieldModel): Airfield model object containing runway and wind data.

        Raises:
            AttributeError: If the provided models are missing expected attributes.
        """
        # --- Verify model like inputs ---
        if is_not_pydantic_model(aircraft_data, airfield_data):
            raise RuntimeError("Expected Pydantic models with .model_dump() method.")

        # --- Aircraft and airfield data instances ---
        self.aircraft_data = aircraft_data
        self.airfield_data = airfield_data

        # --- Aircraft data ---
        self.landing_distance_at_sea_level: int = int(aircraft_data.landing_distance_at_sea_level)
        self.xwind_max_speed: float = float(aircraft_data.xwind_max_speed)
        self.stall_speed: int = int(aircraft_data.stall_speed)

        # --- Airfield data ---
        self.wind: WindModel = self.airfield_data.wind

        # --- Handle and normalize wind speed
        try:
            self.wind.speed
        except (TypeError, ValueError):
            self.wind.speed = 0.0

        # --- Handle and normalize wind direction
        if isinstance(self.wind.direction, str):
            if self.wind.direction.strip().upper() in {"VRB", "CALM", "VAR", ""}:
                self.wind.direction = 0
            else:
                try:
                    self.wind.direction
                except ValueError:
                    self.wind.direction = 0
        else:
            self.wind.direction = 0

        self.wind.direction %= 360

        # --- Parse runways direction ---
        self.runways_direction: set[int] = convert_to_int(self.get_runways_direction())

    def get_runways_direction(self) -> list[str]:
        """
        Retrieve and parse runway direction data from the airfield information.

        Returns:
            list[str]: A list of runway direction identifiers (e.g., ['09', '27']).

        Raises:
            RuntimeError: If runway direction data cannot be retrieved or parsed correctly.
        """
        runways = self.airfield_data.runway
        try:
            runways_direction = [direction
                                 for runway in runways
                                 for direction in runway.direction.split('/')
                                 ]

            return runways_direction

        except KeyError as err:
            logger.error(f"Failed to get runways directions | Error: {err}.")
            raise RuntimeError("Failed to get runways directions. Check runways data format.") from err

    def calculate_xwind_speed(self) -> list[float]:
        """
        Calculate the crosswind (perpendicular) component of the wind for each runway.

        The crosswind is computed as:
            crosswind = wind_speed * sin(wind_direction - runway_direction * 10)

        Returns:
            list[float]: List of crosswind speeds (in the same units as the input wind speed)
                         for each runway direction, rounded to one decimal place.
        """
        runways_directions = self.runways_direction

        # --- Calculations ---
        xwind_speeds = [
            round(self.wind.speed * (sin(radians(self.wind.direction - runway_direction * 10))), 1)
            for runway_direction in runways_directions
        ]

        return xwind_speeds

    def calculate_headwind_speed(self) -> list[float]:
        """
        Calculate the headwind (parallel) component of the wind for each runway.

        The headwind is computed as:
            headwind = wind_speed * cos(wind_direction - runway_direction * 10)

        Returns:
            list[float]: List of headwind speeds (in the same units as the input wind speed)
                         for each runway direction, rounded to one decimal place.
        """
        runways_directions = self.runways_direction

        # --- Calculations ---
        headwinds_speed = [
            round(self.wind.speed * (cos(radians(self.wind.direction - runway_direction * 10))), 1)
            for runway_direction in runways_directions
        ]

        return headwinds_speed

    def calculate_density_altitude(self) -> int:
        """
        Calculate density altitude based on the provided METAR data.
        Falls back to standard pressure altitude if METAR is missing.
        """
        metar = self.airfield_data.metar

        try:
            # --- Handle missing METAR ---
            if not metar or not isinstance(metar, str):
                logger.warning("No valid METAR data available — using default sea level density altitude (0 ft).")
                return 0  # fallback to standard conditions

            # --- Normal parsing logic ---
            pressure = None
            temperature = None

            for token in metar.split():
                # Parse pressure (e.g. Q1013 or A2992)
                if token.startswith("Q") and token[1:].isdigit():
                    pressure = int(token[1:])
                elif token.startswith("A") and token[1:].isdigit():
                    # Inches of Hg to hPa
                    pressure = round(float(token[1:]) * 33.8639)

                # Parse temperature (e.g. 15/10)
                if "/" in token and token.replace("/", "").replace("M", "").isdigit():
                    parts = token.split("/")
                    try:
                        temperature = int(parts[0].replace("M", "-"))
                    except ValueError:
                        continue

            if pressure is None or temperature is None:
                logger.warning(f"Incomplete METAR data for density altitude. Pressure={pressure}, Temp={temperature}")
                return 0

            # --- Compute pressure altitude ---
            field_elevation = getattr(self, "elevation", 0)
            pressure_altitude = field_elevation + (1013 - pressure) * 27

            # --- Compute density altitude ---
            isa_temp = 15 - 0.00198 * field_elevation
            density_altitude = round(pressure_altitude + (120 * (temperature - isa_temp)))

            logger.info(f"Density altitude: {density_altitude} ft")
            return density_altitude

        except Exception as err:
            logger.error(f"Failed to calculate density altitude | Error: {err}")
            raise RuntimeError("Error calculating density altitude.") from err

    def calculate_takeoff_distance(self) -> list[int]:
        wind_speeds = self.calculate_headwind_speed()
        density_altitude = self.calculate_density_altitude()
        density_ratio = exp(- density_altitude / HEIGHT_APPROXIMATION)
        takeoff_speed = self.stall_speed * 1.2
        true_airspeed = convert_to_tas(takeoff_speed, density_ratio)
        ground_speeds = [(true_airspeed - wind_speed) * KNOTS_FACTOR for wind_speed in wind_speeds]
        surface_factor = 0.02
        safety_factor = 1.43
        takeoff_distance = [
            round((ground_speed ** 2) /
                  (2 * GRAVITY_FACTOR * (CALIBRATED_TAKEOFF_FACTOR * density_ratio - surface_factor))
                  * safety_factor)
            for ground_speed in ground_speeds
        ]
        logger.info(f"Required takeoff distance: {takeoff_distance}")

        return takeoff_distance

    def calculate_landing_distance(self) -> list[int]:
        wind_speeds = self.calculate_headwind_speed()
        density_altitude = self.calculate_density_altitude()
        density_ratio = exp(- density_altitude / HEIGHT_APPROXIMATION)
        landing_speed = self.stall_speed * 1.3
        true_airspeed = convert_to_tas(landing_speed, density_ratio)
        ground_speeds = [(true_airspeed - wind_speed) * KNOTS_FACTOR for wind_speed in wind_speeds]
        surface_factor = 1.0
        safety_factor = 1.43
        landing_distance = [
            round(
                ((ground_speed ** 2) /
                 (2 * GRAVITY_FACTOR * (surface_factor + CALIBRATED_LANDING_FACTOR * density_ratio)))
                * safety_factor
            )
            for ground_speed in ground_speeds
        ]
        logger.info(f"Required landing distance: {landing_distance}")

        return landing_distance

    def calculate_required_runway_distance(
            self,
            stall_speed_factor: StallSpeedFactor,
            surface_factor: float = 1.0,
            safety_factor: float = 0.0
    ) -> list[int]:
        """
        Calculates the required runway distance for takeoff or landing.

        Args:
            stall_speed_factor: StallSpeedFactor Enum (TAKEOFF=1.2, LANDING=1.3)
            surface_factor: Runway surface correction (friction etc.)
            safety_factor: Safety margin multiplier (≥1.0)

        Returns:
            List[int]: Required runway distances for each wind direction (in feet)
        """
        # ---Base calculations ---
        wind_speeds = self.calculate_headwind_speed()
        density_altitude = self.calculate_density_altitude()
        density_ratio = exp(- density_altitude / HEIGHT_APPROXIMATION)

        required_speed = self.stall_speed * stall_speed_factor.value
        true_airspeed = convert_to_tas(required_speed, density_ratio)
        ground_speeds = [(true_airspeed - wind_speed) * KNOTS_FACTOR for wind_speed in wind_speeds]

        # --- Choose formula based on operation type ---
        surface_factor = surface_factor
        safety_factor = safety_factor

        if stall_speed_factor == StallSpeedFactor.TAKEOFF:
            factor = CALIBRATED_TAKEOFF_FACTOR * density_ratio - surface_factor
            phase = "takeoff"
        else:
            factor = surface_factor + CALIBRATED_LANDING_FACTOR * density_ratio
            phase = "landing"

        # --- Compute required runway distance ---
        runway_distance = [
            round(
                ((ground_speed ** 2) / (2 * GRAVITY_FACTOR * factor)) * safety_factor
            )
            for ground_speed in ground_speeds
        ]
        logger.info(f"Required {phase} distance: {runway_distance}")

        return runway_distance

    def check_visibility(self) -> int:
        pass

    def check_cloud_base(self) -> int:
        pass

    def submit_recommendation(self) -> Literal["NO GO", "GO IFR", "GO VFR"]:
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
        except requests.RequestException as exc:
            raise exc


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
                        surface=runway.get("surface", None)[0],
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
        # --- Creating model builders instances ---
        departure_airfield_model_builder = AirfieldModelBuilder()
        arrival_airfield_model_builder = AirfieldModelBuilder()
        # recommendation_model_builder = RecommendationModelBuilder()

        # --- Adding data to build airfield models ---
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

        # --- Building airfield and recommendation models ---
        departure_airfield = departure_airfield_model_builder.build()
        arrival_airfield = arrival_airfield_model_builder.build()

        departure_airfield_ops_calculator = AircraftOpsCalculator(
            aircraft_data=self.data.aircraft_data,
            airfield_data=departure_airfield_model_builder.build())
        logger.info(f"Departure airfield wind parameters: {departure_airfield_ops_calculator.wind}")
        logger.info(
            f"Departure airfield crosswind speed: {departure_airfield_ops_calculator.calculate_xwind_speed()} kt")
        logger.info(
            f"Departure airfield headwind speed: {departure_airfield_ops_calculator.calculate_headwind_speed()} kt")
        logger.info(
            f"Departure airfield density altitude: {departure_airfield_ops_calculator.calculate_density_altitude()} ft")
        departure_airfield_ops_calculator.calculate_takeoff_distance()

        arrival_airfield_ops_calculator = AircraftOpsCalculator(
            aircraft_data=self.data.aircraft_data,
            airfield_data=arrival_airfield_model_builder.build())
        logger.info(f"Arrival airfield wind parameters: {arrival_airfield_ops_calculator.wind}")
        logger.info(f"Arrival airfield crosswind speed: {arrival_airfield_ops_calculator.calculate_xwind_speed()} kt")
        logger.info(f"Arrival airfield headwind speed: {arrival_airfield_ops_calculator.calculate_headwind_speed()} kt")
        logger.info(
            f"Arrival airfield density altitude: {arrival_airfield_ops_calculator.calculate_density_altitude()} ft")
        arrival_airfield_ops_calculator.calculate_landing_distance()

        return BriefingModel(
            aircraft=self.data.aircraft_data,
            departure_airfield=departure_airfield,
            arrival_airfield=arrival_airfield,
            recommendation="NO GO",
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


app = FastAPI(debug=True, swagger_ui_parameters={"theme": "dark"})

briefing_store: dict[str, BriefingModel] = {}
briefing_status: dict[str, BriefingStatus] = {}


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

    except HTTPException as exc:
        logger.warning(f"Briefing generation failed due to HTTP error | Details: {exc}")
        raise RuntimeError("Unable to generate briefing")

    except Exception as exc:
        logger.error(msg=f"Unexpected error during briefing generation | Error: {exc}", exc_info=True)
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
