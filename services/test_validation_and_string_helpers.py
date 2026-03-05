import pytest
from django.core.exceptions import ValidationError

from services.validation_service import (
    normalize_serial_number,
    validate_device,
    validate_device_rack_area,
)
from utilities.string import enum_key, remove_linebreaks, title, trailing_slash


class _Rack:
    def __init__(self, area_id):
        self.area_id = area_id


class _Area:
    def __init__(self, area_id):
        self.id = area_id


class _Device:
    def __init__(self, rack, area):
        self.rack = rack
        self.area = area


def test_validate_device_rack_area_requires_area_when_rack_present():
    with pytest.raises(ValidationError) as excinfo:
        validate_device_rack_area(_Device(_Rack(area_id=1), None), _Rack(area_id=1), None)

    assert "Select an area before choosing a rack." in str(excinfo.value)


def test_validate_device_rack_area_rejects_mismatched_rack_area():
    with pytest.raises(ValidationError) as excinfo:
        validate_device_rack_area(_Device(_Rack(area_id=2), _Area(1)), _Rack(area_id=2), _Area(1))

    assert "Selected rack does not belong to the chosen area." in str(excinfo.value)


def test_validate_device_delegates_to_rack_area_validation():
    validate_device(_Device(_Rack(area_id=1), _Area(1)))


def test_string_helpers_cover_common_normalization_cases():
    assert enum_key("Campus Core-1") == "CAMPUS_CORE_1"
    assert remove_linebreaks("line1\nline2\rline3") == "line1line2line3"
    assert title("core SWITCH uplink") == "Core SWITCH Uplink"
    assert trailing_slash("/api/v1") == "api/v1/"
    assert trailing_slash("") == ""


def test_normalize_serial_number_handles_empty_and_placeholders():
    assert normalize_serial_number("  SN-001  ") == "SN-001"
    assert normalize_serial_number("") is None
    assert normalize_serial_number("n/a") is None
    assert normalize_serial_number("UNKNOWN:123") is None
