import datetime

import pytest
from pydantic import ValidationError
from uuid import UUID

from flight_prep_assistant.src.models import BriefingModel


class TestBriefingModel:
    """
    Unit tests for the 'BriefingModel' Pydantic model.

    This test suite verifies:
        - Proper initialization with valid data
        - Validation errors for invalid inputs
        - Correct behavior of default factories (briefing_id, timestamp)
        - Accessibility and correctness of nested models
        - Integrity of computed recommendation
    """

    def test_briefing_model_initializes_with_valid_data(self, briefing_model_fixture):
        """
        Ensure the 'BriefingModel' correctly initializes when provided
        valid input data. Verifies aircraft, airfields, conditions,
        and recommendation fields.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert briefing_model.aircraft.type == "3XTrim"
        assert briefing_model.departure_airfield.elevation == 240
        assert briefing_model.arrival_airfield.elevation == 300
        assert briefing_model.departure_conditions.cloud_base == 15000
        assert briefing_model.arrival_conditions.cloud_base == 5000
        assert briefing_model.recommendation == "GO VFR"

    @pytest.mark.parametrize("payload", [
        pytest.param({"briefing_id": None}, id="briefing_id as None value"),
        pytest.param({"timestamp": ""}, id="timestamp as empty string"),
        pytest.param({"aircraft": True}, id="aircraft as bool"),
        pytest.param({"departure_airfield": ""}, id="departure_airfield as empty string"),
        pytest.param({"arrival_airfield": False}, id="arrival_airfield as bool"),
        pytest.param({"departure_conditions": 1234}, id="departure_conditions as integer"),
        pytest.param({"arrival_conditions": ""}, id="arrival_conditions as empty string"),
        pytest.param({"recommendation": "NO"}, id="incomplete recommendation string"),
    ])
    def test_briefing_model_invalid_types_raise_error(self, payload, briefing_model_fixture):
        """
        Verify that 'BriefingModel' raises a 'ValidationError' when fields
        are provided with invalid types or values. Each payload tests a
        specific invalid scenario.
        """
        with pytest.raises(ValidationError):
            kwargs = briefing_model_fixture(**payload)
            BriefingModel(**kwargs)

    def test_briefing_model_default_factory_generate_valid_briefing_id(self, briefing_model_fixture):
        """
        Ensure that 'briefing_id' is automatically generated as a valid UUID
        when not provided explicitly.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert isinstance(briefing_model.briefing_id, UUID)

    def test_briefing_model_generates_unique_briefing_id(self, briefing_model_fixture):
        """
        Verify that multiple 'BriefingModel' instances generate unique
        'briefing_id' values.
        """
        briefing_model1 = BriefingModel(**briefing_model_fixture())
        briefing_model2 = BriefingModel(**briefing_model_fixture())

        assert briefing_model1.briefing_id != briefing_model2.briefing_id

    def test_briefing_model_default_timestamp_is_set(self, briefing_model_fixture):
        """
        Ensure that the 'timestamp' field can be explicitly provided
        and is correctly set in the model.
        """
        default_timestamp = datetime.datetime(2026, 1, 1, 12, 0, 0)
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs, timestamp=default_timestamp)

        assert briefing_model.timestamp == default_timestamp

    def test_briefing_model_nested_departure_airfield_accessible(self, briefing_model_fixture):
        """
        Verify that all nested fields of the departure airfield are
        accessible and have the expected values.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert briefing_model.departure_airfield.icaoId == "EPKK"
        assert briefing_model.departure_airfield.runway[0].direction == [7, 25]
        assert briefing_model.departure_airfield.runway[0].length == 9000
        assert briefing_model.departure_airfield.runway[0].width == 180
        assert briefing_model.departure_airfield.runway[0].surface == "asphalt"
        assert briefing_model.departure_airfield.elevation == 240
        assert briefing_model.departure_airfield.wind.direction == 150
        assert briefing_model.departure_airfield.wind.speed == 12
        assert briefing_model.departure_airfield.wind.gust == 20
        assert briefing_model.departure_airfield.temperature == 12
        assert briefing_model.departure_airfield.frequency.twr == "120.500"
        assert briefing_model.departure_airfield.metar == "METAR EPKK 081630Z 10002KT 2000 BR OVC002 07/06 Q1015"
        assert briefing_model.departure_airfield.taf == "TAF EPKK 081430Z 0815/0915 08005KT 8000 OVC004"

    def test_briefing_model_nested_arrival_airfield_accessible(self, briefing_model_fixture):
        """
        Verify that all nested fields of the arrival airfield are
        accessible and have the expected values.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert briefing_model.arrival_airfield.icaoId == "EPKT"
        assert briefing_model.arrival_airfield.runway[0].direction == [9, 27]
        assert briefing_model.arrival_airfield.runway[0].length == 10000
        assert briefing_model.arrival_airfield.runway[0].width == 150
        assert briefing_model.arrival_airfield.runway[0].surface == "asphalt"
        assert briefing_model.arrival_airfield.elevation == 300
        assert briefing_model.arrival_airfield.wind.direction == 70
        assert briefing_model.arrival_airfield.wind.speed == 5
        assert briefing_model.arrival_airfield.wind.gust == 10
        assert briefing_model.arrival_airfield.temperature == 5
        assert briefing_model.arrival_airfield.frequency.twr == "129.250"
        assert briefing_model.arrival_airfield.metar == "METAR EPKT 060730Z 07003KT 4500 BR NSC 05/04 Q1020"
        assert briefing_model.arrival_airfield.taf == "TAF EPKT 060530Z 0606/0706 12004KT 1600 BR NSC"

    def test_briefing_model_nested_aircraft_accessible(self, briefing_model_fixture):
        """
        Verify that all nested fields of the aircraft are accessible
        and have the expected values.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert briefing_model.aircraft.type == "3XTrim"
        assert briefing_model.aircraft.mtow == 495
        assert briefing_model.aircraft.takeoff_distance_at_sea_level == 820
        assert briefing_model.aircraft.landing_distance_at_sea_level == 820
        assert briefing_model.aircraft.stall_speed == 38
        assert briefing_model.aircraft.crosswind_max_speed == 12

    def test_briefing_model_nested_departure_conditions_accessible(self, briefing_model_fixture):
        """
        Verify that all nested fields of departure_conditions are accessible
        and match expected values.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert briefing_model.departure_conditions.runway_direction == [7, 25]
        assert briefing_model.departure_conditions.runway_distance == [800, 700]
        assert briefing_model.departure_conditions.crosswind_speed == [6, -6]
        assert briefing_model.departure_conditions.headwind_speed == [-2.1, 2.1]
        assert briefing_model.departure_conditions.visibility == 10000
        assert briefing_model.departure_conditions.cloud_base == 15000

    def test_briefing_model_nested_arrival_conditions_accessible(self, briefing_model_fixture):
        """
        Verify that all nested fields of arrival_conditions are accessible
        and match expected values.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert briefing_model.arrival_conditions.runway_direction == [9, 27]
        assert briefing_model.arrival_conditions.runway_distance == [800, 700]
        assert briefing_model.arrival_conditions.crosswind_speed == [2, -4]
        assert briefing_model.arrival_conditions.headwind_speed == [-3.5, 2.0]
        assert briefing_model.arrival_conditions.visibility == 10000
        assert briefing_model.arrival_conditions.cloud_base == 5000

    def test_briefing_model_recommendation_reflects_conditions(self, briefing_model_fixture):
        """
        Verify that the 'recommendation' field reflects the input conditions
        and nested model data correctly.
        """
        kwargs = briefing_model_fixture()
        briefing_model = BriefingModel(**kwargs)

        assert briefing_model.recommendation == "GO VFR"


@pytest.fixture
def briefing_model_fixture():
    """
    Returns a factory function producing valid base input data for
    'BriefingModel' instances.

    The factory allows overrides to test invalid scenarios.
    """
    def _base_factory(**overrides):
        base = {
            "aircraft": {
                "type": "3XTrim",
                "mtow": 495,
                "takeoff_distance_at_sea_level": 820,
                "landing_distance_at_sea_level": 820,
                "stall_speed": 38,
                "crosswind_max_speed": 12
            },
            "departure_airfield": {
                "icaoId": "EPKK",
                "runway": [{
                    "direction": [7, 25],
                    "length": 9000,
                    "width": 180,
                    "surface": "asphalt",
                }],
                "elevation": 240,
                "wind": {
                    "direction": 150,
                    "speed": 12,
                    "gust": 20,
                },
                "temperature": 12,
                "frequency": {
                    "twr": "120.500"
                },
                "metar": "METAR EPKK 081630Z 10002KT 2000 BR OVC002 07/06 Q1015",
                "taf": "TAF EPKK 081430Z 0815/0915 08005KT 8000 OVC004",
            },
            "arrival_airfield": {
                "icaoId": "EPKT",
                "runway": [{
                    "direction": [9, 27],
                    "length": 10000,
                    "width": 150,
                    "surface": "asphalt",
                }],
                "elevation": 300,
                "wind": {
                    "direction": 70,
                    "speed": 5,
                    "gust": 10,
                },
                "temperature": 5,
                "frequency": {
                    "twr": "129.250"
                },
                "metar": "METAR EPKT 060730Z 07003KT 4500 BR NSC 05/04 Q1020",
                "taf": "TAF EPKT 060530Z 0606/0706 12004KT 1600 BR NSC",
            },
            "departure_conditions": {
                "runway_direction": [7, 25],
                "runway_distance": [800, 700],
                "crosswind_speed": [6, -6],
                "headwind_speed": [-2.1, 2.1],
                "visibility": 10000,
                "cloud_base": 15000
            },
            "arrival_conditions": {
                "runway_direction": [9, 27],
                "runway_distance": [800, 700],
                "crosswind_speed": [2, -4],
                "headwind_speed": [-3.5, 2.0],
                "visibility": 10000,
                "cloud_base": 5000
            },
            "recommendation": "GO VFR",
        }
        base.update(overrides)
        return base

    return _base_factory
