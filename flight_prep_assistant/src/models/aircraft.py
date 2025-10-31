from pydantic import BaseModel, Field


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
