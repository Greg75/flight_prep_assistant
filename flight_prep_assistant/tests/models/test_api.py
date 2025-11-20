import pytest

from pydantic import ValidationError

from flight_prep_assistant.src.models.api import ApiParams, AirfieldParams


class TestApiParams:
    """Unit tests for the ApiParams Pydantic model."""

    def test_api_params_default_format(self):
        """Verify that the 'format' field defaults to 'json'."""
        field_info = ApiParams.model_fields["format"]
        params_default = ApiParams()

        assert field_info.default == "json"
        assert params_default.format == "json"

    def test_api_params_custom_format(self):
        """Verify that a custom value for 'format' can be set."""
        params_custom = ApiParams(format="xml")

        assert params_custom.format == "xml"

    def test_api_params_to_dict(self):
        """Ensure that model serialization via model_dump returns the correct dictionary."""
        api_params = ApiParams()

        assert api_params.model_dump() == {"format": "json"}

    def test_api_params_format_type(self):
        """Confirm that the 'format' field is always stored as a string."""
        api_params = ApiParams(format="xml")

        assert isinstance(api_params.format, str)


class TestAirfieldParams:
    """Test suite for validating the AirfieldParams request model."""

    @pytest.mark.parametrize("payload", [
        pytest.param({"ids": "EP"}, id="too_short"),
        pytest.param({"ids": "LEPKE"}, id="too_long"),
        pytest.param({"ids": "1234"}, id="digits_only"),
        pytest.param({"ids": True}, id="bool"),
    ])
    def test_airfield_params_invalid_ids(self, payload):
        """Ensure invalid ICAO codes trigger a validation error."""
        with pytest.raises(ValidationError) as err:
            AirfieldParams(**payload)

        assert "ids" in str(err.value)

    def test_airfield_params_taf_default(self):
        """Verify that the TAF field defaults to 'true'."""
        taf_field = AirfieldParams.model_fields["taf"]

        assert taf_field.default == "true"
        assert AirfieldParams(ids="EPKK").taf == "true"

    @pytest.mark.parametrize("payload", [
        pytest.param({"ids": "EPKK", "taf": "12"}, id="too_short"),
        pytest.param({"ids": "EPKK", "taf": "123456"}, id="too_long"),
        pytest.param({"ids": "EPKK", "taf": "False"}, id="capitalized_False"),
        pytest.param({"ids": "EPKK", "taf": "True"}, id="capitalized_True"),
    ])
    def test_airfield_params_invalid_taf(self, payload):
        """Confirm that invalid TAF values are rejected with a clear error."""
        with pytest.raises(ValidationError) as err:
            AirfieldParams(**payload)

        assert "taf must be 'true' or 'false'" in str(err.value)

    @pytest.mark.parametrize("code", ["EPKK", "EPWA", "EGUL", "EGUN"])
    def test_airfield_params_valid_icao(self, code):
        """Verify that valid ICAO codes are accepted unchanged."""
        assert AirfieldParams(ids=code).ids == code

    def test_airfield_params_to_dict(self):
        """Ensure model_dump returns correctly normalized and structured output."""
        assert AirfieldParams(ids="epkk", taf="false").model_dump() == {"format": "json", "ids": "EPKK", "taf": "false"}

    def test_airfield_params_inherits_from_api_params(self):
        """Check that AirfieldParams properly inherits from ApiParams."""
        assert issubclass(AirfieldParams, ApiParams)
