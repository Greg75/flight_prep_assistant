from main import InputData, AircraftModel


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
