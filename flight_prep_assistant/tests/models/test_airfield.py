import pytest
from pydantic import ValidationError

from flight_prep_assistant.src.models import RunwayModel, WindModel, FrequencyModel, AirfieldModel


class TestRunwayModel:
    """Tests validation and normalization logic of RunwayModel fields: direction, dimensions, and surface."""

    # --- Runway direction tests ---
    def test_runway_direction_is_none(self):
        """Ensure direction defaults to None when not provided."""
        runway_model = RunwayModel()

        assert runway_model.direction is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": "09/27"}, id="plain_string"),
        pytest.param({"direction": "09L/27R"}, id="string_with_letters"),
        pytest.param({"direction": ["09", "27"]}, id="list_of_strings"),
        pytest.param({"direction": [9, 27]}, id="list_of_integers"),
    ])
    def test_runway_direction_valid_input_types(self, payload):
        """Verify valid direction formats normalize to a numeric list."""
        runway_model = RunwayModel(**payload)

        assert runway_model.direction == [9, 27]

    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": 1234}, id="plain_integer"),
        pytest.param({"direction": ("abcd", "abcd")}, id="tuple_of_strings"),
        pytest.param({"direction": {1234, 5678}}, id="set_of_integers"),
        pytest.param({"direction": {"1": 1234, "2": 5678}}, id="dict_of_integers"),
    ])
    def test_runway_direction_invalid_input_types(self, payload):
        """Ensure invalid direction types raise TypeError."""
        with pytest.raises(TypeError):
            RunwayModel(**payload)

    # --- Runway length and width tests ---
    def test_length_and_width_is_none(self):
        """Ensure length and width default to None when not provided."""
        runway_model = RunwayModel()

        assert runway_model.length is None
        assert runway_model.width is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"length": 1000, "width": 50}, id="plain_integers"),
        pytest.param({"length": "1000", "width": "50"}, id="plain_strings"),
        pytest.param({"length": "1000ft", "width": "50 ft"}, id="strings_with_units"),
    ])
    def test_length_and_width_valid_input_types(self, payload):
        """Validate numeric or unit-appended inputs normalize to integers."""
        runway_model = RunwayModel(**payload)

        assert runway_model.length == 1000
        assert runway_model.width == 50

    @pytest.mark.parametrize("payload, expected_error", [
        pytest.param({"length": [1000, 900], "width": [50, 40]}, TypeError, id="list_of_integers"),
        pytest.param({"length": ["1000", "900"], "width": ["abc50", "def40"]}, TypeError, id="list_of_strings"),
        pytest.param({"length": "abcd", "width": "ef"}, ValueError, id="strings_no_digits"),
    ])
    def test_length_and_width_invalid_input_types(self, payload, expected_error):
        """Ensure invalid length/width formats raise the expected error."""
        with pytest.raises(expected_error):
            RunwayModel(**payload)

    # --- Runway surface tests ---
    def test_surface_is_none(self):
        """Ensure surface defaults to None when not provided."""
        runway_model = RunwayModel()

        assert runway_model.surface is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"surface": "asphalt"}, id="lowercase"),
        pytest.param({"surface": "Asphalt"}, id="capitalized"),
        pytest.param({"surface": "ASPHALT"}, id="uppercase"),
    ])
    def test_surface_valid_input_types(self, payload):
        """Verify surface input is normalized to lowercase."""
        runway_model = RunwayModel(**payload)

        assert runway_model.surface == "asphalt"

    @pytest.mark.parametrize("payload", [
        pytest.param({"surface": 1234}, id="plain_integer"),
        pytest.param({"surface": "concrete1234"}, id="string_and_integer"),
        pytest.param({"surface": " concrete "}, id="invalid_whitespaces"),
    ])
    def test_surface_invalid_input_types(self, payload):
        """Ensure invalid surface formats raise ValidationError."""
        with pytest.raises(ValidationError):
            RunwayModel(**payload)


class TestWindModel:
    """Test suite for validating the WindModel's handling of direction, speed, and gust fields."""

    # --- Wind direction tests ---
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
        pytest.param({"direction": 0, "speed": 10}, id="int 0 as direction"),
        pytest.param({"direction": "0", "speed": 10}, id="str 0 as direction"),
    ])
    def test_direction_zero_is_valid_and_returns_zero_for_int_and_string(self, payload):
        wind_model = WindModel(**payload)

        assert wind_model.direction == 0

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

    # --- Wind speed tests ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"direction": 120, "speed": -10}, id="negative int"),
        pytest.param({"direction": 120, "speed": "-10"}, id="negative str"),
    ])
    def test_speed_must_be_non_negative(self, payload):
        """Ensure that wind speed cannot be negative, regardless of input type."""
        with pytest.raises(ValidationError):
            WindModel(**payload)

    # --- Wind gust tests ---
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
    """
    Tests FrequencyModel behavior: whitespace stripping, None handling,
    type validation, and acceptance of extra fields.
    """

    def test_frequency_model_accepts_valid_twr(self, frequency_model_fixture):
        """Verify that a valid TWR frequency is accepted and preserved after validation."""
        frequency_model = frequency_model_fixture

        assert frequency_model.twr == "130.500"

    def test_frequency_model_strips_whitespace_in_twr(self):
        """Ensure leading and trailing whitespace in the TWR field is removed."""
        frequency_model = FrequencyModel(twr=" 130.500 ")

        assert frequency_model.twr == "130.500"

    def test_frequency_model_allows_none_twr(self):
        """Confirm that the TWR field can be set to None without raising validation errors."""
        frequency_model = FrequencyModel(twr=None)

        assert frequency_model.twr is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"twr": 130.500}, id="frequency as an int"),
        pytest.param({"twr": True}, id="frequency as a bool"),
    ])
    def test_frequency_model_rejects_invalid_field_types(self, payload):
        """Validate that incorrect data types for the TWR field raise a ValidationError."""
        with pytest.raises(ValidationError):
            FrequencyModel(**payload)

    def test_frequency_model_allows_extra_fields(self, frequency_model_fixture):
        """Verify that the model accepts and preserves extra fields when extra='allow' is enabled."""
        frequency_model = frequency_model_fixture.model_dump()

        assert frequency_model["app"] == "120.500"
        assert frequency_model["gnd"] == "110.500"


@pytest.fixture
def frequency_model_fixture():
    """
    Fixture providing a FrequencyModel instance that includes valid TWR data
    and additional extra fields to test validation and extra field handling.
    """
    return FrequencyModel.model_validate({"twr": " 130.500 ", "app": "120.500", "gnd": " 110.500 "})


class TestAirfieldModel:
    """
    Test suite validating the behavior, constraints, and normalization logic of the AirfieldModel.
    The tests cover field-level validation, optional-field handling, numerical bounds, list validation,
    nested model behavior, and correct initialization of the full model payload.
    """

    # --- ICAO ID validation ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"icaoId": "EPKK"}, id="valid uppercase ICAO Id"),
        pytest.param({"icaoId": " EPKK"}, id="uppercase ICAO Id with leading whitespace"),
        pytest.param({"icaoId": " epkk "}, id="lowercase ICAO Id with leading and trailing whitespace"),
    ])
    def test_airfield_icao_valid_code_is_accepted(self, payload, airfield_model_fixture):
        """
        Verify that valid ICAO identifiers—including variations with whitespace and case differences—
        are normalized and accepted by the AirfieldModel.
        """
        kwargs = airfield_model_fixture(**payload)
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.icaoId == "EPKK"

    @pytest.mark.parametrize("payload", [
        pytest.param({"icaoId": ""}, id="empty ICAO Id"),
        pytest.param({"icaoId": "ep12"}, id="invalid ICAO Id"),
    ])
    def test_airfield_icao_empty_string_raises_error(self, payload, airfield_model_fixture):
        """
        Ensure that invalid ICAO identifiers (e.g., empty strings or malformed codes)
        trigger a validation error during model initialization.
        """
        with pytest.raises(ValidationError):
            kwargs = airfield_model_fixture(**payload)
            AirfieldModel(**kwargs)

    # --- Runway List validation ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"runway": []}, id="empty runway list"),
    ])
    def test_airfield_runway_list_empty_raises_error(self, payload, airfield_model_fixture):
        """
        Confirm that an empty runway list is rejected and results in a validation error,
        as at least one runway entry is required.
        """
        with pytest.raises(ValidationError):
            kwargs = airfield_model_fixture(**payload)
            airfield_model = AirfieldModel(**kwargs)

    def test_airfield_runway_valid_list_is_accepted(self, airfield_model_fixture):
        """
        Validate that a properly structured runway list is accepted and that all nested
        runway attributes are correctly parsed and available.
        """
        kwargs = airfield_model_fixture()
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.runway[0].direction == [9, 27]
        assert airfield_model.runway[0].length == 9000
        assert airfield_model.runway[0].width == 180
        assert airfield_model.runway[0].surface == "asphalt"

    # --- Elevation validation ---
    def test_airfield_elevation_within_range_is_accepted(self, airfield_model_fixture):
        """
        Verify that elevation values within the defined range are accepted by the model.
        """
        kwargs = airfield_model_fixture()
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.elevation == 240

    @pytest.mark.parametrize("payload", [
        pytest.param({"elevation": -1001}, id='elevation below minimum'),
        pytest.param({"elevation": 15001}, id='elevation above maximum'),
    ])
    def test_airfield_elevation_exceeding_range_raises_error(self, payload, airfield_model_fixture):
        """
        Ensure that elevation values outside the allowed range cause a validation error.
        """
        with pytest.raises(ValidationError):
            kwargs = airfield_model_fixture(**payload)
            AirfieldModel(**kwargs)

    @pytest.mark.parametrize("payload", [
        pytest.param({"elevation": None}, id='elevation as None'),
    ])
    def test_airfield_elevation_none_is_allowed(self, payload, airfield_model_fixture):
        """
        Confirm that elevation may be set to None when the field is optional and that the
        model accepts such input without error.
        """
        kwargs = airfield_model_fixture(**payload)
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.elevation is None

    # --- Temperature validation ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"temperature": 20.1234}, id='temperature rounded to one decimal'),
    ])
    def test_airfield_temperature_is_rounded_to_one_decimal(self, payload, airfield_model_fixture):
        """
        Validate that temperature values are rounded to one decimal place according to
        the model's data normalization rules.
        """
        kwargs = airfield_model_fixture(**payload)
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.temperature == 20.1

    @pytest.mark.parametrize("payload", [
        pytest.param({"temperature": None}, id='temperature as None'),
    ])
    def test_airfield_temperature_none_is_allowed(self, payload, airfield_model_fixture):
        """
        Ensure that temperature may be assigned a None value when the field is optional
        and that the model accepts this input without error.
        """
        kwargs = airfield_model_fixture(**payload)
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.temperature is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"temperature": -81}, id='temperature below minimum'),
        pytest.param({"temperature": 61}, id='temperature above maximum'),
    ])
    def test_airfield_temperature_exceeding_range_raises_error(self, payload, airfield_model_fixture):
        """
        Confirm that temperature values falling outside the defined allowable range
        result in a validation error.
        """
        with pytest.raises(ValidationError):
            kwargs = airfield_model_fixture(**payload)
            AirfieldModel(**kwargs)

    # --- Wind, Frequency, METAR, TAF basic behavior validation ---
    @pytest.mark.parametrize("payload", [
        pytest.param({"wind": ""}, id='wind as empty string'),
        pytest.param({"wind": None}, id='wind as None'),
    ])
    def test_airfield_wind_model_empty_or_none_raises_error(self, payload, airfield_model_fixture):
        """
        Ensure that the wind field rejects empty or null values when a valid nested
        WindModel instance is required.
        """
        with pytest.raises(ValidationError):
            kwargs = airfield_model_fixture(**payload)
            AirfieldModel(**kwargs)

    @pytest.mark.parametrize("payload", [
        pytest.param({"frequency": ""}, id='frequency as empty string'),
        pytest.param({"frequency": None}, id='frequency as None'),
    ])
    def test_airfield_frequency_model_empty_or_none_raises_error(self, payload, airfield_model_fixture):
        """
        Verify that the frequency field rejects empty or null values when a valid nested
        FrequencyModel instance is required.
        """
        with pytest.raises(ValidationError):
            kwargs = airfield_model_fixture(**payload)
            AirfieldModel(**kwargs)

    @pytest.mark.parametrize("payload", [
        pytest.param({"metar": None}, id='metar as None'),
    ])
    def test_airfield_metar_optional_field_accepts_none(self, payload, airfield_model_fixture):
        """
        Confirm that the optional METAR field accepts None and initializes correctly.
        """
        kwargs = airfield_model_fixture(**payload)
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.metar is None

    @pytest.mark.parametrize("payload", [
        pytest.param({"taf": None}, id='taf as None'),
    ])
    def test_airfield_taf_optional_field_accepts_none(self, payload, airfield_model_fixture):
        """
        Ensure that the optional TAF field accepts None and initializes correctly.
        """
        kwargs = airfield_model_fixture(**payload)
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.taf is None

    # --- Full model validation ---
    def test_airfield_model_initializes_with_valid_data(self, airfield_model_fixture):
        """
        Validate that a complete and fully valid payload initializes the AirfieldModel
        without raising validation errors and that all fields contain the expected values.
        """
        kwargs = airfield_model_fixture()
        airfield_model = AirfieldModel(**kwargs)

        assert airfield_model.icaoId == "EPKK"
        assert airfield_model.runway[0].direction == [9, 27]
        assert airfield_model.runway[0].length == 9000
        assert airfield_model.runway[0].width == 180
        assert airfield_model.runway[0].surface == "asphalt"
        assert airfield_model.elevation == 240
        assert airfield_model.wind.direction == 150
        assert airfield_model.wind.speed == 12
        assert airfield_model.wind.gust == 20
        assert airfield_model.temperature == 12
        assert airfield_model.frequency.twr == "120.500"
        assert airfield_model.metar == "METAR EPKK 081630Z 10002KT 2000 BR OVC002 07/06 Q1015"
        assert airfield_model.taf == "TAF EPKK 081430Z 0815/0915 08005KT 8000 OVC004"

    @pytest.mark.parametrize("payload", [
        pytest.param({"runway": []}, id='empty runway list'),
        pytest.param({"wind": ""}, id='missing wind value'),
        pytest.param({"frequency": ""}, id='missing frequency value'),
    ])
    def test_airfield_model_rejects_missing_required_fields(self, payload, airfield_model_fixture):
        """
        Confirm that missing or invalid required fields cause the AirfieldModel initialization
        to fail with a validation error.
        """
        with pytest.raises(ValidationError):
            kwargs = airfield_model_fixture(**payload)
            AirfieldModel(**kwargs)


@pytest.fixture
def airfield_model_fixture():
    """
    Provide a factory that constructs a complete, valid base payload for initializing
    an AirfieldModel instance. The fixture returns a callable that accepts arbitrary
    field overrides, merges them with the predefined baseline attributes, and produces
    a dictionary suitable for model instantiation.

    This pattern enables individual tests to supply only the fields under examination
    while relying on consistent, known-good defaults for all other required fields.

    Returns:
        Callable[..., dict]: A function that generates a fully populated AirfieldModel
        payload with optional per-test overrides applied.
    """
    def _base_factory(**overrides):
        base = {"icaoId": "EPKK",
                "runway": [{
                    "direction": [9, 27],
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
                }
        base.update(overrides)
        return base

    return _base_factory
