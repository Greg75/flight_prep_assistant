import pytest
from pydantic import ValidationError

from flight_prep_assistant.src.models import RunwayModel, WindModel


class TestRunwayModel:

    # --- Runway direction tests ---
    def test_runway_direction_is_none(self):
        runway_model = RunwayModel()

        assert runway_model.direction is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": "09/27"}, id="plain_string"),
        pytest.param({"direction": "09L/27R"},  id="string_with_letters"),
        pytest.param({"direction": ["09", "27"]}, id="list_of_strings"),
        pytest.param({"direction": [9, 27]}, id="list_of_integers"),
    ])
    def test_runway_direction_valid_input_types(self, payload):
        runway_model = RunwayModel(**payload)

        assert runway_model.direction == [9, 27]

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": 1234}, id="plain_integer"),
        pytest.param({"direction": ("abcd", "abcd")}, id="tuple_of_strings"),
        pytest.param({"direction": {1234, 5678}}, id="set_of_integers"),
        pytest.param({"direction": {"1": 1234, "2": 5678}}, id="dict_of_integers"),
    ])
    def test_runway_direction_invalid_input_types(self, payload):

        with pytest.raises(TypeError):
            RunwayModel(**payload)

    # --- Runway length and width tests ---
    def test_length_and_width_is_none(self):
        runway_model = RunwayModel()

        assert runway_model.length is None
        assert runway_model.width is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"length": 1000, "width": 50}, id="plain_integers"),
        pytest.param({"length": "1000", "width": "50"}, id="plain_strings"),
        pytest.param({"length": "1000ft", "width": "50 ft"}, id="strings_with_units"),
    ])
    def test_length_and_width_valid_input_types(self, payload):
        runway_model = RunwayModel(**payload)

        assert runway_model.length == 1000
        assert runway_model.width == 50

    @pytest.mark.parametrize("payload, expected_error", [
        pytest.param({"length": [1000, 900], "width": [50, 40]}, TypeError, id="list_of_integers"),
        pytest.param({"length": ["1000", "900"], "width": ["abc50", "def40"]}, TypeError, id="list_of_strings"),
        pytest.param({"length": "abcd", "width": "ef"}, ValueError, id="strings_no_digits"),
    ])
    def test_length_and_width_invalid_input_types(self, payload, expected_error):
        with pytest.raises(expected_error):
            RunwayModel(**payload)

    # --- Runway surface tests ---
    def test_surface_is_none(self):
        runway_model = RunwayModel()

        assert runway_model.surface is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"surface": "asphalt"}, id="lowercase"),
        pytest.param({"surface": "Asphalt"}, id="capitalized"),
        pytest.param({"surface": "ASPHALT"}, id="uppercase"),
    ])
    def test_surface_valid_input_types(self, payload):
        runway_model = RunwayModel(**payload)

        assert runway_model.surface == "asphalt"

    @pytest.mark.parametrize("payload", [
        pytest.param({"surface": 1234}, id="plain_integer"),
        pytest.param({"surface": "concrete1234"}, id="string_and_integer"),
        pytest.param({"surface": " concrete "}, id="invalid_whitespaces"),
    ])
    def test_surface_invalid_input_types(self, payload):
        with pytest.raises(ValidationError):
            RunwayModel(**payload)


class TestWindModel:
    """Test suite for validating the WindModel's handling of direction, speed, and gust fields."""

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": 60, "speed": 10}, id="direction as int in range 0-360"),
        pytest.param({"direction": 420, "speed": 10}, id="direction as int exceeding range 0-360 once"),
        pytest.param({"direction": 780, "speed": 10}, id="direction as int exceeding range 0-360 twice"),
    ])
    def test_direction_int_is_normalized_mod_360(self, payload):
        """Ensure integer wind direction values are normalized using modulo 360."""
        wind_model = WindModel(**payload)

        assert wind_model.direction == 60

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": "VRB", "speed": 10}, id="VRB returns 0"),
        pytest.param({"direction": "calm", "speed": 10}, id="lowercase 'calm' returns 0"),
        pytest.param({"direction": "VAR", "speed": 10}, id="VAR returns 0"),
        pytest.param({"direction": "", "speed": 10}, id="Empty string returns 0"),
    ])
    def test_direction_string_valid_returns_zero(self, payload):
        """Verify that known non-numeric string directions are interpreted as 0 degrees."""
        wind_model = WindModel(**payload)

        assert wind_model.direction == 0

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": "60", "speed": 10}, id="direction as str in range 0-360"),
        pytest.param({"direction": "420", "speed": 10}, id="direction as str exceeding range 0-360 once"),
        pytest.param({"direction": "780", "speed": 10}, id="direction as str exceeding range 0-360 twice"),
    ])
    def test_direction_string_numeric_is_converted_to_int_and_mod_360(self, payload):
        """Check that numeric strings are converted to integers and normalized with modulo 360."""
        wind_model = WindModel(**payload)

        assert wind_model.direction == 60

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": "1a3", "speed": 10}, id="string with alphanumeric characters"),
        pytest.param({"direction": 2.5, "speed": 10}, id="float number"),
        pytest.param({"direction": True, "speed": 10}, id="boolean value"),
    ])
    def test_direction_string_invalid_raises_value_error(self, payload):
        """Validate that invalid direction values raise a Pydantic ValidationError."""
        with pytest.raises(ValidationError):
            WindModel(**payload)

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": 120, "speed": -10}, id="negative int"),
        pytest.param({"direction": 120, "speed": "-10"}, id="negative str"),
    ])
    def test_speed_must_be_non_negative(self, payload):
        """Ensure that wind speed cannot be negative, regardless of input type."""
        with pytest.raises(ValidationError):
            WindModel(**payload)

    def test_gust_greater_than_speed_is_valid(self):
        """Verify that gust values greater than speed are accepted."""
        wind_model = WindModel(direction=120, speed=10, gust=12)

        assert wind_model.gust > wind_model.speed

    def test_gust_equal_to_speed_is_valid(self):
        """Confirm that gust equal to speed is accepted."""
        wind_model = WindModel(direction=120, speed=10, gust=10)

        assert wind_model.gust == wind_model.speed

    def test_gust_less_than_speed_raises_value_error(self):
        """Check that gust values below wind speed result in a validation error."""
        with pytest.raises(ValidationError):
            WindModel(direction=120, speed=10, gust=8)

    def test_gust_none_is_accepted(self):
        """Ensure gust may be omitted or set to None without validation errors."""
        wind_model = WindModel(direction=120, speed=10)

        assert wind_model.gust is None


class TestFrequencyModel:
    pass


class TestAirfieldModel:
    pass
