import pytest
from pydantic import ValidationError

from flight_prep_assistant.src.models.request_data import InputData


class TestInputData:
    """
    Test suite for the InputData Pydantic model.

    This class verifies correct initialization with valid input data
    and ensures that invalid values are properly rejected by model
    validation rules.
    """

    def test_input_data_initializes_with_valid_data(self, input_data_model_fixture):
        """
        Verify that InputData initializes correctly when provided
        with a fully valid payload.

        Ensures that all top-level fields and nested aircraft_data
        attributes are correctly parsed and assigned.
        """
        input_data_model = InputData(**input_data_model_fixture())

        assert input_data_model.departure_airfield == "EPKK"
        assert input_data_model.arrival_airfield == "EPKT"
        assert input_data_model.aircraft_data.type == "3XTrim"
        assert input_data_model.aircraft_data.mtow == 495
        assert input_data_model.aircraft_data.takeoff_distance_at_sea_level == 350
        assert input_data_model.aircraft_data.landing_distance_at_sea_level == 250
        assert input_data_model.aircraft_data.stall_speed == 35
        assert input_data_model.aircraft_data.crosswind_max_speed == 12

    @pytest.mark.parametrize("payload", [
        pytest.param({"departure_airfield": "EPK"}, id="ICAO code to short"),
        pytest.param({"departure_airfield": "EPKKK"}, id="ICAO code to long"),
        pytest.param({"departure_airfield": ""}, id="ICAO code as empty string"),
        pytest.param({"departure_airfield": 1234}, id="ICAO code as integer"),
    ])
    def test_input_data_rejects_invalid_departure_airfield(self, payload, input_data_model_fixture):
        """
        Ensure that invalid departure_airfield values are rejected.

        Covers incorrect ICAO code length, invalid data types,
        and empty values.
        """
        kwargs = input_data_model_fixture(**payload)

        with pytest.raises(ValidationError):
            InputData(**kwargs)

    @pytest.mark.parametrize("payload", [
        pytest.param({"arrival_airfield": "EPK"}, id="ICAO code to short"),
        pytest.param({"arrival_airfield": "EPKKK"}, id="ICAO code to long"),
        pytest.param({"arrival_airfield": ""}, id="ICAO code as empty string"),
        pytest.param({"arrival_airfield": 1234}, id="ICAO code as integer"),
    ])
    def test_input_data_rejects_invalid_arrival_airfield(self, payload, input_data_model_fixture):
        """
        Ensure that invalid arrival_airfield values are rejected.

        Covers incorrect ICAO code length, invalid data types,
        and empty values.
        """
        kwargs = input_data_model_fixture(**payload)

        with pytest.raises(ValidationError):
            InputData(**kwargs)

    @pytest.mark.parametrize("payload", [
        pytest.param({"aircraft_data": {"type": "3X"}}, id="Type to short"),
        pytest.param({"aircraft_data": {"mtow": -495}}, id="Negative mass"),
        pytest.param({"aircraft_data": {"takeoff_distance_at_sea_level": -250}}, id="Negative takeoff distance"),
        pytest.param({"aircraft_data": {"landing_distance_at_sea_level": -250}}, id="Negative landing distance"),
        pytest.param({"aircraft_data": {"stall_speed": -25}}, id="Negative stall speed"),
        pytest.param({"aircraft_data": {"crosswind_max_speed": -12}}, id="Negative crosswind max speed"),
    ])
    def test_input_data_rejects_invalid_aircraft_model(self, payload, input_data_model_fixture):
        """
        Ensure that invalid aircraft_data values are rejected.

        Covers domain constraints such as non-negative numeric values
        and minimum length requirements for aircraft type identifiers.
        """
        kwargs = input_data_model_fixture(**payload)

        with pytest.raises(ValidationError):
            InputData(**kwargs)


@pytest.fixture
def input_data_model_fixture():
    """
    Factory fixture for generating valid InputData payloads.

    Returns a callable that produces a complete, valid base payload,
    allowing selective field overrides for negative and edge-case tests.
    """
    def _input_data_model_factory(**overrides):
        """
        Build an InputData-compatible dictionary with optional overrides.

        Args:
            **overrides: Keyword arguments used to override default
                         payload fields or nested structures.

        Returns:
            dict: A dictionary suitable for initializing InputData.
        """
        base = {
            "departure_airfield": "EPKK",
            "arrival_airfield": "EPKT",
            "aircraft_data": {
                "type": "3XTrim",
                "mtow": 495,
                "takeoff_distance_at_sea_level": 350,
                "landing_distance_at_sea_level": 250,
                "stall_speed": 35,
                "crosswind_max_speed": 12,
            }
        }
        base.update(overrides)
        return base
    return _input_data_model_factory
