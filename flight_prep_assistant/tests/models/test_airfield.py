import pytest
from pydantic import ValidationError

from flight_prep_assistant.src.models import RunwayModel


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
