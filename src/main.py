import os
import requests
from enum import Enum
from dotenv import load_dotenv
from requests import Response
from pydantic import BaseModel, Field

load_dotenv()


# Helper classes and functions
class InputData(BaseModel):
    """
    Represents input data required for flight planning.

    Attributes:
        departure_airfield (str): The ICAO code of the departure airfield. Must be exactly 4 alphabetical characters.
        arrival_airfield (str): The ICAO code of the arrival airfield. Must be exactly 4 alphabetical characters.
        aircraft_type (str): The aircraft type identifier. Must be at least 4 characters long.
    """
    departure_airfield: str = Field(min_length=4, max_length=4, pattern=r'^[A-Za-z]{4}$')
    arrival_airfield: str = Field(min_length=4, max_length=4, pattern=r'^[A-Za-z]{4}$')
    aircraft_type: str = Field(min_length=4)


def get_input() -> InputData:
    """
    Prompts the user to enter flight planning data via standard input.

    Returns:
        InputData: A validated instance containing the departure airfield, arrival airfield, and aircraft type.

    Notes:
        - ICAO codes are automatically converted to uppercase.
        - Raises a ValidationError if the input does not meet the model's constraints.
    """
    return InputData(
        departure_airfield=input("Departure airfield ICAO code: ").upper(),
        arrival_airfield=input("Arrival airfield ICAO code: ").upper(),
        aircraft_type=input("Aircraft type: "),
    )


# Basic classes
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
    def __init__(self, api_url_key: str):
        """
        Initializes the API client with a base URL resolved from an environment variable.

        Args:
            api_url_key (str): The environment variable key holding the base URL.
        """
        self.api_url = os.getenv(api_url_key)

        if not self.api_url:
            raise ValueError(f"Environment variable '{api_url_key}' not set or empty.")

    def load_data(self, **params) -> Response:
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
            response = requests.get(url=self.api_url, params=params)
            return response
        except requests.RequestException as exp:
            raise exp


def main():
    airfield_api = ApiClient(api_url_key=ApiUrlKey.AIRFIELD.value)
    weather_api = ApiClient(api_url_key=ApiUrlKey.WEATHER.value)
    data_inputs = get_input()
    print(f"Departure airfield: {airfield_api.load_data(
        ids=data_inputs.departure_airfield, 
        format="json").json()}",
        )
    print(f"Departure WX: {weather_api.load_data(
        ids=data_inputs.departure_airfield, 
        format="json").json()}",
        )
    print(f"Arrival airfield: {airfield_api.load_data(
        ids=data_inputs.arrival_airfield, 
        format="json").json()}",
        )
    print(f"Arrival WX: {weather_api.load_data(
        ids=data_inputs.arrival_airfield,
        format="json").json()}",
        )
    print(f"Aircraft: {data_inputs.aircraft_type}")


if __name__ == "__main__":
    main()
