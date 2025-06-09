import os
import requests
import time
from enum import Enum
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Self, Optional
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

load_dotenv()


# Models classes
class RunwayModel(BaseModel):
    """
    Represents a runway at an airfield.

    Attributes:
        direction (str | None): The runway's direction identifier (e.g., "09/27").
        length (str | None): The total length of the runway, typically in meters or feet.
        width (str): The width of the runway, typically in meters or feet.
        surface (str): The surface type of the runway (e.g., asphalt, grass).
    """

    direction: Optional[str] = Field(
        default=None, pattern=r"^\d{2,3}|\d{2}[L|R]/\d{2,3}|\d{2}[L|R]$"
    )
    length: Optional[str] = Field(default=None, pattern=r"^\d{3,5}$")
    width: Optional[str] = Field(default=None, pattern=r"^\d{2,3}$")
    surface: Optional[str] = Field(default=None, pattern=r"^[a-zA-Z]{1,99}$")


class WindModel(BaseModel):
    """
    Represents wind conditions at an airfield.

    Attributes:
        direction (int | str | None): The wind direction in degrees, or descriptive text.
        speed (float | None): The wind speed in knots or meters per second.
    """

    direction: Optional[int | str] = None
    speed: Optional[float] = None


class FrequencyModel(BaseModel):
    """
    Represents communication frequencies for an airfield.

    Attributes:
        twr (str): Tower frequency.
    """

    twr: Optional[str] = None

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

    icaoId: Optional[str] = None
    runway: List[RunwayModel]
    elevation: Optional[int] = None
    wind: WindModel
    temperature: Optional[float] = None
    frequency: FrequencyModel
    metar: Optional[str] = None
    taf: Optional[str] = None


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

    type: str = Field(min_length=3)
    mtow: int
    takeoff_distance_at_sea_level: int
    landing_distance_at_sea_level: int
    stall_speed: int
    xwind_max_speed: float


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

    briefing_id: UUID
    aircraft: AircraftModel
    departure_airfield: AirfieldModel
    arrival_airfield: AirfieldModel
    recommendation: Literal["NO GO", "GO IFR", "GO VFR"]


class BriefingStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in progress"
    COMPLETE = "complete"
    ERROR = "error"


class InputData(BaseModel):
    """
    Represents input data required for flight planning.

    Attributes:
        departure_airfield (str): The ICAO code of the departure airfield. Must be exactly 4 alphabetical characters.
        arrival_airfield (str): The ICAO code of the arrival airfield. Must be exactly 4 alphabetical characters.
        aircraft_data (str): The aircraft type identifier. Must be at least 4 characters long.
    """

    departure_airfield: str = Field(
        min_length=4, max_length=4, pattern=r"^[A-Za-z]{4}$"
    )
    arrival_airfield: str = Field(min_length=4, max_length=4, pattern=r"^[A-Za-z]{4}$")
    aircraft_data: AircraftModel


class ApiParams(BaseModel):
    """
    The base parameter for API request.

    Attributes:
        format (str): The expected format of the API response (e.g., "json", "xml"). Defaults to "json".
    """

    format: str = "json"


class AirfieldParams(ApiParams):
    """
    Parameters specific to airfield data API requests.

    Attributes:
        ids (str): The ICAO identifier of the airfield to query.
        taf (str): Whether to include TAF (Terminal Aerodrome Forecast) data in the response. Defaults to "true".
    """

    ids: str
    taf: str = "true"


class AircraftParams(ApiParams):
    """
    Parameters specific to aircraft data API requests.

    Attributes:
        api_key (str): The API key used for authentication and authorization.
        manufacturer (str): The name of the aircraft manufacturer to filter the results (e.g., "Boeing", "Airbus").
    """

    api_key: str
    manufacturer: str


# Helper functions
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
        mtow=int(input("Max takeoff weight: ")),
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


# Base classes
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
        self.briefing = briefing_model
        self.aircraft = briefing_model.aircraft.model_dump()
        self.departure = briefing_model.departure_airfield.model_dump()
        self.arrival = briefing_model.arrival_airfield.model_dump()
        self.html: Optional[HTML] = None

    def render_briefing_html(self) -> HTML:
        """
        Render the briefing data into HTML using a Jinja2 template.

        Returns:
            HTML: A WeasyPrint HTML object containing the rendered briefing.
        """
        template_dir = Path(__file__).parent
        environment = Environment(loader=FileSystemLoader(template_dir))
        template = environment.get_template("briefing.html")

        html_output = template.render(
            departure=self.departure,
            arrival=self.arrival,
            aircraft=self.aircraft,
        )

        self.html = HTML(string=html_output)
        return self.html

    def write_briefing_pdf(self) -> Path:
        """
        Write the rendered HTML briefing to a PDF file.

        The filename is constructed using the departure and arrival ICAO codes
        and the current date (e.g., Flight_Briefing_KJFK_to_EGLL_2025-06-04.pdf).

        Returns:
            Path: The file path of the generated PDF.
        """
        if self.html is None:
            raise ValueError("HTML content is not rendered. Call render_briefing_html() first.")

        dep_icao = self.departure.get("icaoId", None)
        arr_icao = self.arrival.get("icaoId", None)
        date_str = datetime.today().date().isoformat()
        output_filename = f"Flight_Briefing_{dep_icao}_to_{arr_icao}_{date_str}.pdf"
        output_path = Path.cwd() / output_filename

        self.html.write_pdf(str(output_path))
        return output_path


class ApiUrlKey(Enum):
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

    def add_airfield_data(self, airfield_api: ApiClient, params: AirfieldParams) -> Self:
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


def create_api_client() -> tuple[ApiClient, ApiClient]:
    """
    Create and return API clients for airfield and weather services.

    Returns:
        tuple[ApiClient, ApiClient]: A tuple containing the API clients for airfield and weather data respectively.
    """
    airfield_api = ApiClient(api_url_key=ApiUrlKey.AIRFIELD)
    weather_api = ApiClient(api_url_key=ApiUrlKey.WEATHER)

    return airfield_api, weather_api


def create_api_params(data: InputData) -> tuple[AirfieldParams, AirfieldParams]:
    """
    Generate API parameters for retrieving airfield data based on the input flight data.

    Args:
        data (InputData): The input data containing identifiers for departure and arrival airfields.

    Returns:
        tuple[AirfieldParams, AirfieldParams]: A tuple containing the parameters for the departure and arrival airfields.
    """
    departure_params = AirfieldParams(ids=data.departure_airfield)
    arrival_params = AirfieldParams(ids=data.arrival_airfield)

    return departure_params, arrival_params


def create_airfield_model(airfield_api: ApiClient, weather_api: ApiClient, airfield_api_params: AirfieldParams
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
    airfield_model_builder.add_airfield_data(airfield_api=airfield_api, params=airfield_api_params)
    airfield_model_builder.add_weather_data(weather_api=weather_api, params=airfield_api_params)

    airfield_model = airfield_model_builder.build()

    return airfield_model


def create_briefing_model(data: InputData, departure_airfield: AirfieldModel, arrival_airfield: AirfieldModel
                          ) -> BriefingModel:
    """
    Create a briefing model that consolidates all necessary flight information.

    Args:
        data (InputData): The input flight data including aircraft information.
        departure_airfield (AirfieldModel): The model for the departure airfield.
        arrival_airfield (AirfieldModel): The model for the arrival airfield.

    Returns:
        BriefingModel: A fully populated briefing model with metadata and recommendations.
    """
    return BriefingModel(
        briefing_id=uuid4(),
        aircraft=data.aircraft_data,
        departure_airfield=departure_airfield,
        arrival_airfield=arrival_airfield,
        recommendation="NO GO"
    )


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


@app.get(path="/",
         summary="Root endpoint for Briefing API",
         description="This is the root endpoint of the Briefing API. It simply returns a message indicating "
                     "that the API is running and operational.")
def root() -> dict:
    """
    Root endpoint for the Briefing API.

    Returns:
        dict: A simple message indicating that the API is running.
    """
    return {"message": "Briefing API is running."}


@app.get(path="/ping",
         summary="Ping the API to check its health",
         description="This endpoint returns a status message indicating that the API is healthy and responsive. "
                     "It's often used to check if the API is up and running.")
def ping_api() -> dict:
    """
    Health check endpoint to verify the API is responsive.

    Returns:
        dict: A status message indicating the API is healthy.
    """
    return {"status": "healthy"}


@app.post(path="/generate",
          response_model=BriefingModel,
          summary="Generate a flight briefing based on input data",
          description="This endpoint generates a flight briefing based on the provided input data, "
                      "including details like departure and arrival airfields. It returns a structured "
                      "BriefingModel containing all briefing information for the flight.")
def generate_briefing(data: InputData) -> BriefingModel:
    """
    Generates a flight briefing based on input data.

    Args:
        data (InputData): The input parameters including departure and arrival details.

    Returns:
        BriefingModel: A structured model containing briefing information.
    """
    airfield_api, weather_api = create_api_client()
    departure_params, arrival_params = create_api_params(data=data)

    departure_airfield = create_airfield_model(
        airfield_api=airfield_api,
        weather_api=weather_api,
        airfield_api_params=departure_params
    )

    arrival_airfield = create_airfield_model(
        airfield_api=airfield_api,
        weather_api=weather_api,
        airfield_api_params=arrival_params
    )

    briefing_model = create_briefing_model(
        data=data,
        departure_airfield=departure_airfield,
        arrival_airfield=arrival_airfield
    )

    briefing_store.update(
        {
            str(briefing_model.briefing_id): briefing_model
        }
    )

    return briefing_model


@app.get(path="/briefing/{briefing_id}/download",
         response_model=Path,
         summary="Download a briefing as a PDF",
         description="This endpoint allows you to download a generated flight briefing as a PDF "
                     "using the provided briefing ID. If the briefing ID is invalid, a 404 error will be returned. "
                     "If there are issues during PDF generation, a 500 error will be raised.")
def download_briefing(briefing_id: str) -> Path:
    """
    Downloads the PDF version of a generated flight briefing.

    Args:
        briefing_id (str): The ID of the briefing to download.

    Returns:
        Path: The file path to the generated PDF.

    Raises:
        HTTPException: If the briefing ID is not found or PDF generation fails.
    """
    briefing_status.update({briefing_id: BriefingStatus.PENDING})
    briefing_model = briefing_store.get(briefing_id)

    time.sleep(15)
    briefing_status.update({briefing_id: BriefingStatus.IN_PROGRESS})
    briefing = Briefing(briefing_model)
    briefing.render_briefing_html()

    time.sleep(5)
    briefing_status.update({briefing_id: BriefingStatus.COMPLETE})

    return briefing.write_briefing_pdf()


@app.get(path="/briefing/{briefing_id}/status",
         summary="Check the status of a briefing",
         description="This endpoint allows you to retrieve the current status of a briefing by providing "
                     "the briefing ID. If the briefing ID exists, it returns the corresponding status. "
                     "If the briefing ID is invalid, the status will be `None` or an error.")
def check_status(briefing_id: str) -> dict:
    """
    Check the current status of a briefing.

    Args:
        briefing_id (str): The unique identifier of the briefing.

    Returns:
        dict: A dictionary containing the briefing ID and its current status.
    """
    return {briefing_id: briefing_status.get(briefing_id)}


if __name__ == "__main__":
    pass
