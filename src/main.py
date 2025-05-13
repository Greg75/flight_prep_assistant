import os
import requests
from enum import Enum
from dotenv import load_dotenv
from requests import Response

load_dotenv()


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
    print(airfield_api.load_data(ids="epwa", format="json").json())
    print(weather_api.load_data(ids="epkk"))


if __name__ == "__main__":
    main()
