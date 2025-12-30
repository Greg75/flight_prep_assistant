from pydantic import BaseModel, Field


class AircraftModel(BaseModel):
    """
    Represents performance characteristics of an aircraft.

    Attributes:
        type (str): Aircraft type or model name.
        mtow (int): Maximum takeoff weight in pounds.
        takeoff_distance_at_sea_level (int): Required takeoff distance at sea level under standard conditions [ft].
        landing_distance_at_sea_level (int): Required landing distance at sea level under standard conditions [ft].
        stall_speed (int): Stall speed of the aircraft in knots.
        crosswind_max_speed (int): Maximum crosswind speed the aircraft can handle, in knots.
    """

    type: str = Field(min_length=3, description="Aircraft type or model name.")
    mtow: int = Field(gt=0, description="Maximum takeoff weight in pounds.")
    takeoff_distance_at_sea_level: int = Field(
        gt=0,
        description="Required takeoff distance at sea level in ISA conditions."
    )
    landing_distance_at_sea_level: int = Field(
        gt=0,
        description="Required landing distance at sea level in ISA conditions."
    )
    stall_speed: int = Field(gt=0, description="Stall speed of the aircraft in knots.")
    crosswind_max_speed: float = Field(
        gt=0,
        description="Maximum crosswind speed the aircraft can handle, in knots."
    )
