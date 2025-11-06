import time
from functools import wraps
from logging import getLogger
from math import sqrt

from .models.aircraft import AircraftModel
from .models.request_data import InputData

logger = getLogger(__name__)


# --- Helper functions ---
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
        crosswind_max_speed=float(input("Max crosswind speed: ")),
    )

    return InputData(
        departure_airfield=departure_airfield,
        arrival_airfield=arrival_airfield,
        aircraft_data=aircraft_data,
    )


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


def convert_to_tas(ias: float, density_ratio: float) -> int:
    """
    Convert indicated airspeed (IAS) to true airspeed (TAS) given the air density.

    True airspeed increases as air density decreases. This function uses the
    standard relation between IAS and TAS:

        TAS = IAS / sqrt(density_ratio)

    where 'density_ratio' is the ratio of air density at the current altitude
    to the standard sea-level air density (σ = ρ / ρ0).

    Args:
        ias (float): Indicated airspeed in knots.
        density_ratio (float): Air density ratio (0 < σ ≤ 1).

    Returns:
        int: True airspeed in knots, rounded to the nearest integer.
    """
    return round(ias / sqrt(density_ratio))


def is_greater(value: int, limit: int) -> bool:
    """
    Check if a given value exceeds a specified limit.

    Args:
        value (int): The value to compare.
        limit (int): The threshold to compare against.

    Returns:
        bool: True if the value is greater than the limit, otherwise False.
    """
    return value > limit


def is_not_pydantic_model(*models) -> bool:
    """
    Determine whether any of the provided objects are not Pydantic models.

    Args:
        *models: One or more objects to check.

    Returns:
        bool: True if at least one object does not implement the 'model_dump' method
        (i.e., is not a Pydantic model); False if all are Pydantic models.
    """
    return not all(hasattr(model, "model_dump") for model in models)


def submit_final_recommendation(departure: str, arrival: str) -> str:
    """
    Determine the final flight recommendation based on departure and arrival conditions.

    Args:
        departure (str): The recommendation for the departure airfield (e.g., "GO VFR", "GO IFR", "NO GO").
        arrival (str): The recommendation for the arrival airfield.

    Returns:
        str: The final combined recommendation:
            - "NO GO" if either location is not suitable for flight.
            - "GO IFR" if both require IFR, or if conditions differ.
            - "GO VFR" only if both are suitable for VFR.
    """
    departure_recommendation = departure
    arrival_recommendation = arrival

    if departure_recommendation == "NO GO" or arrival_recommendation == "NO GO":
        return "NO GO"

    if departure_recommendation == "GO IFR" and arrival_recommendation == "GO IFR":
        return "GO IFR"

    if departure_recommendation == "GO VFR" and arrival_recommendation == "GO VFR":
        return "GO VFR"

    return "GO IFR"


def remove_duplicates_elements(value: list) -> list:
    """
    Remove duplicate elements from a list while preserving the original order.

    This function uses a dictionary to maintain insertion order and eliminate
    repeated items efficiently. The first occurrence of each element is kept.

    Args:
        value (list): The input list that may contain duplicate elements.

    Returns:
        list: A new list containing only unique elements in their original order.
    """
    return list(dict.fromkeys(value))
