import pytest

from pydantic import ValidationError

from flight_prep_assistant.src.models.api import ApiParams, AirfieldParams, AircraftParams


class TestApiParams:
    """Unit tests for the ApiParams Pydantic model."""

    # --- Model structure ---
    def test_api_params_model_schema_contains_expected_fields(self):
        """
        Verify that the JSON schema of ApiParams contains the expected 'format' property.

        This ensures that the model's schema includes the 'format' field, which is required
        for correct API serialization and validation.
        """
        api_params = ApiParams.model_json_schema()

        assert "format" in api_params["properties"]

    # --- Serialization ---
    def test_api_params_to_dict(self):
        """Ensure that model serialization via model_dump returns the correct dictionary."""
        api_params = ApiParams()

        assert api_params.model_dump() == {"format": "json"}

    # --- Default values ---
    def test_api_params_default_format(self):
        """Verify that the 'format' field defaults to 'json'."""
        field_info = ApiParams.model_fields["format"]
        params_default = ApiParams()

        assert field_info.default == "json"
        assert params_default.format == "json"

    # --- Valid input ---
    def test_api_params_custom_format(self):
        """Verify that a custom value for 'format' can be set."""
        params_custom = ApiParams(format="xml")

        assert params_custom.format == "xml"

    # --- Data type ---
    def test_api_params_format_type(self):
        """Confirm that the 'format' field is always stored as a string."""
        api_params = ApiParams(format="xml")

        assert isinstance(api_params.format, str)


class TestAirfieldParams:
    """Test suite for validating the AirfieldParams request model."""

    # --- Inheritance ---
    def test_airfield_params_inherits_from_api_params(self):
        """Check that AirfieldParams properly inherits from ApiParams."""
        assert issubclass(AirfieldParams, ApiParams)

    # --- Model structure ---
    def test_airfield_params_model_schema_contains_expected_fields(self):
        """
        Verify that the JSON schema of AirfieldParams contains the expected properties.

        This ensures that the generated schema includes:
        - 'format'
        - 'ids'
        - 'taf'
        which are required for correct API serialization and validation.
        """
        airfield_params = AirfieldParams.model_json_schema()

        assert "format" in airfield_params["properties"]
        assert "ids" in airfield_params["properties"]
        assert "taf" in airfield_params["properties"]

    # --- Serialization ---
    def test_airfield_params_to_dict(self):
        """Ensure model_dump returns correctly normalized and structured output."""
        assert AirfieldParams(ids="epkk", taf="false").model_dump() == {"format": "json", "ids": "EPKK", "taf": "false"}

    # --- Default values ---
    def test_airfield_params_taf_default(self):
        """Verify that the TAF field defaults to 'true'."""
        taf_field = AirfieldParams.model_fields["taf"]

        assert taf_field.default == "true"
        assert AirfieldParams(ids="EPKK").taf == "true"

    # --- Valid inputs ---
    @pytest.mark.parametrize("code", ["EPKK", "EPWA", "EGUL", "EGUN"])
    def test_airfield_params_valid_icao(self, code):
        """Verify that valid ICAO codes are accepted unchanged."""
        assert AirfieldParams(ids=code).ids == code

    # --- Invalid inputs ---
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


class TestAircraftParams:
    """
    Test suite for the AircraftParams Pydantic model.

    This class verifies that:
    - required fields ('api_key' and 'manufacturer) must be provided,
    - valid string inputs are accepted,
    - invalid or empty inputs raise appropriate validation errors,
    - the model serializes correctly via 'model_dump',
    - field metadata (descriptions, schema properties) is correctly defined,
    - the model inherits from the ApiParams base class,
    - and the internal field definitions and JSON schema contain the expected fields.
    """

    # --- Inheritance ---
    def test_aircraft_params_inherits_from_api_params(self):
        """Check that AircraftParams properly inherits from ApiParams."""
        assert issubclass(AircraftParams, ApiParams)

    # --- Model structure ---
    def test_aircraft_params_field_descriptions_are_set(self):
        """Verify that both fields have the correct description metadata."""
        fields_info = AircraftParams.model_fields

        assert fields_info["api_key"].description == "The API key used for authentication and authorization."
        assert fields_info["manufacturer"].description == "The name of the aircraft manufacturer."

    def test_aircraft_params_model_schema_contains_expected_fields(self):
        """Validate that the generated JSON schema lists the expected properties."""
        json_schema = AircraftParams.model_json_schema()

        assert "api_key" in json_schema["properties"]
        assert "manufacturer" in json_schema["properties"]

    def test_aircraft_params_to_dict_returns_expected_fields(self):
        """Confirm that the model defines the expected field names in 'model_fields'."""
        aircraft_params_fields = AircraftParams.model_fields

        assert "api_key" in aircraft_params_fields
        assert "manufacturer" in aircraft_params_fields

    # --- Serialization ---
    def test_aircraft_params_serializes_correctly(self):
        """Verify that model_dump() returns the expected dictionary representation."""
        assert (AircraftParams(
            api_key="valid_key", manufacturer="Boeing"
        ).model_dump() == {
            "format": "json",
            "api_key": "valid_key",
            "manufacturer": "Boeing"
        }
                )

    # --- Valid inputs ---
    def test_aircraft_params_accepts_valid_strings(self):
        """Verify that valid string values for both fields create a valid AircraftParams instance."""
        aircraft_params = AircraftParams(api_key="valid_key", manufacturer="Boeing")

        assert aircraft_params.api_key == "valid_key"
        assert aircraft_params.manufacturer == "Boeing"

    # --- Invalid inputs ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"api_key": None, "manufacturer": "Boeing"}, id="api_key as None"),
        pytest.param({"api_key": True, "manufacturer": "Boeing"}, id="api_key as bool"),
        pytest.param({"api_key": 1234, "manufacturer": "Boeing"}, id="api_key as integer"),
    ])
    def test_aircraft_params_invalid_field_type_for_api_key(self, payload):
        """Ensure invalid data types for 'api_key' raise a ValidationError."""
        with pytest.raises(ValidationError):
            AircraftParams(**payload)

    @pytest.mark.parametrize("payload", [
        pytest.param({"api_key": "valid_key", "manufacturer": None}, id="manufacturer as None"),
        pytest.param({"api_key": "valid_key", "manufacturer": False}, id="manufacturer as bool"),
        pytest.param({"api_key": "valid_key", "manufacturer": 1234}, id="manufacturer as integer"),
    ])
    def test_aircraft_params_invalid_field_type_for_manufacturer(self, payload):
        """Ensure invalid data types for `manufacturer` raise a ValidationError."""
        with pytest.raises(ValidationError):
            AircraftParams(**payload)

    def test_aircraft_params_rejects_empty_manufacturer(self):
        """Ensure an empty string for 'manufacturer' is rejected by validation."""
        with pytest.raises(ValidationError):
            AircraftParams(api_key="valid_key", manufacturer="")

    # --- Required fields ---
    def test_aircraft_params_requires_api_key(self):
        """Ensure creating AircraftParams without 'api_key' raises a ValidationError."""
        with pytest.raises(ValidationError):
            AircraftParams(manufacturer="Boeing")  # type: ignore[call-arg]

    def test_aircraft_params_requires_manufacturer(self):
        """Ensure creating AircraftParams without 'manufacturer' raises a ValidationError."""
        with pytest.raises(ValidationError):
            AircraftParams(api_key="valid_key")  # type: ignore[call-arg]
