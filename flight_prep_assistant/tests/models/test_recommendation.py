import pytest
from pydantic_core._pydantic_core import ValidationError

from flight_prep_assistant.src.models import RecommendationBaseModel, RecommendationExtendModel, \
    RecommendationFinalModel


class TestRecommendationBaseModel:
    """
    Tests for RecommendationBaseModel, which represents the core operational
    and environmental data required to evaluate runway and weather conditions.
    """

    def test_recommendation_base_model_initializes_with_valid_data(self, recommendation_model_fixture):
        """
        Verify that RecommendationBaseModel initializes successfully
        when provided with a complete and valid payload.
        """
        kwargs = recommendation_model_fixture()
        recommendation_model = RecommendationBaseModel(**kwargs)

        assert recommendation_model.runway_direction == [7, 25]
        assert recommendation_model.runway_distance == [9000, 8100]
        assert recommendation_model.crosswind_speed == [7.5, 12.0]
        assert recommendation_model.headwind_speed == [5.0, 2.5]
        assert recommendation_model.visibility == 5000
        assert recommendation_model.cloud_base == 1500

    @pytest.mark.parametrize("payload", [
        pytest.param({"runway_direction": 1000}, id="runway_direction as int"),
        pytest.param({"runway_distance": 1000}, id="runway_distance as int"),
        pytest.param({"crosswind_speed": 2}, id="crosswind_speed as int"),
        pytest.param({"headwind_speed": "vrb"}, id="headwind_speed as str"),
        pytest.param({"visibility": "cavok"}, id="visibility as str"),
        pytest.param({"cloud_base": "clear"}, id="cloud_base as str"),
    ])
    def test_recommendation_base_model_invalid_types_raise_validation_error(
            self, payload, recommendation_model_fixture
    ):
        """
        Ensure that invalid field types are rejected and raise a ValidationError.
        """
        kwargs = recommendation_model_fixture(**payload)
        with pytest.raises(ValidationError):
            RecommendationBaseModel(**kwargs)

    def test_recommendation_base_model_runway_direction_accessible(self, recommendation_model_fixture):
        """
        Verify that runway_direction is accessible and preserves list ordering.
        """
        kwargs = recommendation_model_fixture()
        recommendation_model = RecommendationBaseModel(**kwargs)

        assert recommendation_model.runway_direction[0] == 7

    def test_recommendation_base_model_runway_distance_accessible(self, recommendation_model_fixture):
        """
        Verify that runway_distance values are accessible after model initialization.
        """
        kwargs = recommendation_model_fixture()
        recommendation_model = RecommendationBaseModel(**kwargs)

        assert recommendation_model.runway_distance[0] == 9000

    def test_recommendation_base_model_crosswind_speed_accessible(self, recommendation_model_fixture):
        """
        Verify that crosswind_speed values are accessible and correctly typed.
        """
        kwargs = recommendation_model_fixture()
        recommendation_model = RecommendationBaseModel(**kwargs)

        assert recommendation_model.crosswind_speed[0] == 7.5

    def test_recommendation_base_model_headwind_speed_accessible(self, recommendation_model_fixture):
        """
        Verify that headwind_speed values are accessible and correctly typed.
        """
        kwargs = recommendation_model_fixture()
        recommendation_model = RecommendationBaseModel(**kwargs)

        assert recommendation_model.headwind_speed[0] == 5.0

    def test_recommendation_base_model_visibility_accessible(self, recommendation_model_fixture):
        """
        Verify that visibility is accessible and stored as a scalar value.
        """
        kwargs = recommendation_model_fixture()
        recommendation_model = RecommendationBaseModel(**kwargs)

        assert recommendation_model.visibility == 5000

    def test_recommendation_base_model_cloud_base_accessible(self, recommendation_model_fixture):
        """
        Verify that cloud_base is accessible and stored as a scalar value.
        """
        kwargs = recommendation_model_fixture()
        recommendation_model = RecommendationBaseModel(**kwargs)

        assert recommendation_model.cloud_base == 1500


class TestRecommendationExtendModel:
    """
    Tests for RecommendationExtendModel, which extends the base recommendation
    with a computed or user-defined go/no-go decision.
    """

    def test_recommendation_extend_model_inherits_base_fields(self):
        """
        Verify that RecommendationExtendModel exposes all fields
        defined in RecommendationBaseModel.
        """
        expected_fields = {
            "runway_direction",
            "runway_distance",
            "crosswind_speed",
            "headwind_speed",
            "visibility",
            "cloud_base",
        }

        assert expected_fields.issubset(RecommendationExtendModel.model_fields.keys())

    def test_recommendation_extend_model_default_recommendation_is_no_go(self, recommendation_model_fixture):
        """
        Verify that the default recommendation value is 'NO GO'
        when no explicit recommendation is provided.
        """
        kwargs = recommendation_model_fixture()
        recommendation_extend_model = RecommendationExtendModel(**kwargs)

        assert recommendation_extend_model.recommendation == "NO GO"

    @pytest.mark.parametrize("payload", [
        pytest.param({"recommendation": True}, id="recommendation as bool"),
        pytest.param({"recommendation": 1234}, id="recommendation as int"),
        pytest.param({"recommendation": "GO"}, id="recommendation as int"),
        pytest.param({"recommendation": ""}, id="recommendation as int"),
    ])
    def test_recommendation_extend_model_invalid_recommendation_raises_error(
            self, payload, recommendation_model_fixture
    ):
        """
        Ensure that invalid recommendation values are rejected
        and raise a ValidationError.
        """
        kwargs = recommendation_model_fixture(**payload)
        with pytest.raises(ValidationError):
            RecommendationExtendModel(**kwargs)


class TestRecommendationFinalModel:
    """
    Tests for RecommendationFinalModel, which aggregates departure and arrival
    recommendations and exposes a final operational decision.
    """

    def test_recommendation_final_model_initializes_with_valid_data(self, recommendation_extend_model_fixture):
        """
        Verify that RecommendationFinalModel initializes successfully
        with valid departure, arrival, and final recommendation values.
        """
        departure = RecommendationExtendModel(**recommendation_extend_model_fixture())
        arrival = RecommendationExtendModel(**recommendation_extend_model_fixture())

        recommendation_final_model = RecommendationFinalModel(
            departure=departure,
            arrival=arrival,
            final_recommendation="GO VFR"
        )

        assert recommendation_final_model.departure.recommendation == "GO VFR"
        assert recommendation_final_model.arrival.recommendation == "GO VFR"
        assert recommendation_final_model.final_recommendation == "GO VFR"

    def test_recommendation_final_model_departure_and_arrival_accessible(self, recommendation_extend_model_fixture):
        """
        Verify that departure and arrival RecommendationExtendModel instances
        are accessible and preserve their internal data.
        """
        departure = RecommendationExtendModel(**recommendation_extend_model_fixture())
        arrival = RecommendationExtendModel(**recommendation_extend_model_fixture())

        recommendation_final_model = RecommendationFinalModel(
            departure=departure,
            arrival=arrival,
            final_recommendation="NO GO"
        )

        assert recommendation_final_model.departure.runway_direction == [7, 25]
        assert recommendation_final_model.departure.recommendation == "GO VFR"
        assert recommendation_final_model.arrival.runway_direction == [7, 25]
        assert recommendation_final_model.arrival.recommendation == "GO VFR"

    def test_recommendation_final_model_final_recommendation_accessible(self, recommendation_extend_model_fixture):
        """
        Verify that the final_recommendation field is accessible
        and preserves the assigned value.
        """
        departure = RecommendationExtendModel(**recommendation_extend_model_fixture())
        arrival = RecommendationExtendModel(**recommendation_extend_model_fixture())

        recommendation_final_model = RecommendationFinalModel(
            departure=departure,
            arrival=arrival,
            final_recommendation="GO IFR"
        )

        assert recommendation_final_model.final_recommendation == "GO IFR"

    @pytest.mark.parametrize("payload", [
        pytest.param({"final_recommendation": True}, id="recommendation as bool"),
        pytest.param({"final_recommendation": 1234}, id="recommendation as int"),
        pytest.param({"final_recommendation": "MAYBE"}, id="recommendation as invalid str"),
        pytest.param({"final_recommendation": ""}, id="recommendation as empty str"),
    ])
    def test_recommendation_final_model_invalid_final_recommendation_raises_error(
            self, payload, recommendation_extend_model_fixture
    ):
        """
        Ensure that invalid final recommendation values are rejected
        and raise a ValidationError.
        """
        departure = RecommendationExtendModel(**recommendation_extend_model_fixture())
        arrival = RecommendationExtendModel(**recommendation_extend_model_fixture())

        with pytest.raises(ValidationError):
            RecommendationFinalModel(
                departure=departure,
                arrival=arrival,
                **payload,
            )


@pytest.fixture
def recommendation_model_fixture():
    """
    Factory fixture producing a valid payload for RecommendationBaseModel,
    with optional field overrides for negative testing.
    """
    def _base_factory(**overrides):
        base = {
            "runway_direction": [7, 25],
            "runway_distance": [9000, 8100],
            "crosswind_speed": [7.5, 12.0],
            "headwind_speed": [5.0, 2.5],
            "visibility": 5000,
            "cloud_base": 1500,
        }
        base.update(overrides)
        return base
    return _base_factory


@pytest.fixture
def recommendation_extend_model_fixture():
    """
    Factory fixture producing a valid payload for RecommendationExtendModel,
    including a pre-defined recommendation value, with optional overrides.
    """
    def _base_factory(**overrides):
        base = {
            "runway_direction": [7, 25],
            "runway_distance": [9000, 8100],
            "crosswind_speed": [7.5, 12.0],
            "headwind_speed": [5.0, 2.5],
            "visibility": 5000,
            "cloud_base": 1500,
            "recommendation": "GO VFR",
        }
        base.update(overrides)
        return base
    return _base_factory
