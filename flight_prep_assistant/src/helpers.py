import re
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
        xwind_max_speed=float(input("Max crosswind speed: ")),
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


def convert_to_int(runways_direction: list[str]) -> set[int]:
    """
    Convert a list of runway direction strings into a set of integers.
    Handles letters, slashes, empty items, and logs the result.
    """
    converted = set()
    for rwy in runways_direction:
        try:
            nums = re.findall(
                pattern=r"\d+",
                string=rwy)
            if nums:
                converted.add(int(nums[0]))
        except Exception as e:
            logger.warning(f"Skipping invalid runway entry '{rwy}': {e}")

    logger.info(f"Runways extracted, converted to integers: {converted}")
    return converted


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


def is_within_limits():
    pass


def is_not_pydantic_model(*models) -> bool:
    return not all(hasattr(model, "model_dump") for model in models)


def is_not_valid_icao_code(icao: str, pattern: str = r"^[A-Za-z]{4}$") -> bool:
    return not re.fullmatch(pattern=pattern, string=icao)
