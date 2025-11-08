import pytest
from pydantic import ValidationError

from flight_prep_assistant.src.models import AircraftModel


class TestAircraftModel:

    # --- Valid input data creates aircraft model instance ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="c152_correct_input"),
        pytest.param({"type": "3XTrim",
                      "mtow": 495,
                      "takeoff_distance_at_sea_level": 820,
                      "landing_distance_at_sea_level": 820,
                      "stall_speed": 38,
                      "crosswind_max_speed": 12}, id="3xtrim_correct_input"),
    ])
    def test_valid_data_creates_instance(self, payload):
        """Test that AircraftModel is successfully created with valid input data."""
        aircraft_model = AircraftModel(**payload)

        assert isinstance(aircraft_model, AircraftModel)
        for key, value in payload.items():
            assert getattr(aircraft_model, key) == value

    # --- Invalid input data raises an error ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"type": "C1",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="type_too_short"),
        pytest.param({"type": None,
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="missing_type"),
        pytest.param({"type": "C152",
                      "mtow": None,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="missing_mtow"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": -725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 0,
                      "crosswind_max_speed": 12}, id="negative_takeoff_roll"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": -475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="negative_landing_roll"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 0,
                      "crosswind_max_speed": 12}, id="stall_speed_zero"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 0}, id="crosswind_max_speed_zero"),
        pytest.param({}, id="all_fields_missing"),
    ])
    def test_invalid_or_missing_value_raises_validation_error(self, payload):
        """Test that AircraftModel raises ValidationError for invalid or missing field values."""

        with pytest.raises(ValidationError):
            AircraftModel(**payload)

    @pytest.mark.parametrize("payload", [
        pytest.param({"type": 152,
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="type_not_string"),
        pytest.param({"type": "C152",
                      "mtow": "heavy",
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="mtow_not_integer"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": "725ft",
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 0,
                      "crosswind_max_speed": 12}, id="takeoff_roll_not_integer"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": "475m",
                      "stall_speed": 43,
                      "crosswind_max_speed": 12}, id="landing_roll_not_integer"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": "fast",
                      "crosswind_max_speed": 12}, id="stall_speed_not_integer"),
        pytest.param({"type": "C152",
                      "mtow": 757,
                      "takeoff_distance_at_sea_level": 725,
                      "landing_distance_at_sea_level": 475,
                      "stall_speed": 43,
                      "crosswind_max_speed": "UNK"}, id="crosswind_max_speed_not_integer"),
    ])
    def test_invalid_input_data_types_raises_validation_error(self, payload):
        """Test that AircraftModel raises ValidationError for invalid input type values."""

        with pytest.raises(ValidationError):
            AircraftModel(**payload)
