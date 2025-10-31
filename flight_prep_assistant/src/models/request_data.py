from pydantic import BaseModel, Field

from .aircraft import AircraftModel


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
                        "takeoff_distance_at_sea_level": 918,
                        "landing_distance_at_sea_level": 918,
                        "stall_speed": 38,
                        "xwind_max_speed": 12,
                    },
                }
            ]
        }
    }
