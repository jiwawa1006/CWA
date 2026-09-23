"""
test_validation.py - Unit tests for Gate 4: Data Validation Layer.
"""

from pathlib import Path
import pandas as pd
import pytest

from validate_weather import (
    validate_weather_dataframe,
    is_valid_calendar_date,
    WeatherValidationError,
    ValidationResult
)
from parse_weather import parse_weather_data

SAMPLE_FILE = Path(__file__).parent / "sample_weather.json"


def test_valid_sample_data_passes_validation():
    """Ensure that valid parsed sample weather data passes validation cleanly."""
    raw_df = parse_weather_data(SAMPLE_FILE)
    result = validate_weather_dataframe(raw_df)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.validated_df) == len(raw_df)
    assert result.dropped_rows == 0


def test_missing_required_columns_detected():
    """Ensure that DataFrame missing required schema columns is rejected."""
    bad_df = pd.DataFrame({
        "regionName": ["北部地區"],
        "dataDate": ["2026-04-14"],
        "minT": [18.0]
        # Missing maxT
    })
    result = validate_weather_dataframe(bad_df)
    assert result.is_valid is False
    assert any("Missing required columns: maxT" in err for err in result.errors)


def test_missing_or_empty_fields_detected():
    """Ensure that missing regionName or dataDate is detected."""
    df_missing = pd.DataFrame([
        {"regionName": "", "dataDate": "2026-04-14", "minT": 18.0, "maxT": 25.0},
        {"regionName": None, "dataDate": "2026-04-14", "minT": 18.0, "maxT": 25.0},
        {"regionName": "北部地區", "dataDate": None, "minT": 18.0, "maxT": 25.0},
        {"regionName": "中部地區", "dataDate": "2026-04-14", "minT": None, "maxT": 25.0},
        {"regionName": "南部地區", "dataDate": "2026-04-14", "minT": 18.0, "maxT": None},
    ])
    result = validate_weather_dataframe(df_missing)
    assert result.is_valid is False
    assert len(result.errors) >= 5
    assert result.valid_rows == 0
    assert result.dropped_rows == 5


def test_invalid_date_format_detected():
    """Ensure invalid date strings (non-existent calendar dates or bad formats) are rejected."""
    df_bad_dates = pd.DataFrame([
        {"regionName": "北部地區", "dataDate": "2026-02-30", "minT": 18.0, "maxT": 25.0},  # Feb 30 does not exist
        {"regionName": "中部地區", "dataDate": "not-a-date", "minT": 20.0, "maxT": 28.0},
        {"regionName": "南部地區", "dataDate": "2026/04/14", "minT": 22.0, "maxT": 30.0},  # Slash format not normalized
    ])
    result = validate_weather_dataframe(df_bad_dates)
    assert result.is_valid is False
    assert any("dataDate '2026-02-30' is invalid" in err for err in result.errors)
    assert any("dataDate 'not-a-date' is invalid" in err for err in result.errors)
    assert result.valid_rows == 0


def test_temperature_inversion_rejected():
    """Ensure that minT > maxT is detected and rejected with clear error message."""
    df_inverted = pd.DataFrame([
        {"regionName": "北部地區", "dataDate": "2026-04-14", "minT": 32.0, "maxT": 20.0},  # Inverted!
        {"regionName": "中部地區", "dataDate": "2026-04-14", "minT": 20.0, "maxT": 28.0},  # Valid
    ])
    result = validate_weather_dataframe(df_inverted)
    assert result.is_valid is False
    assert any("minT (32.0) cannot be greater than maxT (20.0)" in err for err in result.errors)
    assert result.valid_rows == 1
    assert result.dropped_rows == 1
    assert result.validated_df.iloc[0]["regionName"] == "中部地區"


def test_temperature_physical_bounds_detected():
    """Ensure extreme temperatures outside plausible Taiwan range are detected."""
    df_extreme = pd.DataFrame([
        {"regionName": "北部地區", "dataDate": "2026-04-14", "minT": -40.0, "maxT": 20.0},  # Below -15
        {"regionName": "南部地區", "dataDate": "2026-04-14", "minT": 25.0, "maxT": 60.0},   # Above 45
    ])
    result = validate_weather_dataframe(df_extreme)
    assert result.is_valid is False
    assert any("exceeds realistic bounds" in err for err in result.errors)
    assert result.valid_rows == 0


def test_duplicate_records_detected():
    """Ensure duplicate regionName + dataDate records are detected and deduplicated."""
    df_dup = pd.DataFrame([
        {"regionName": "北部地區", "dataDate": "2026-04-14", "minT": 18.0, "maxT": 25.0},
        {"regionName": "北部地區", "dataDate": "2026-04-14", "minT": 19.0, "maxT": 26.0},  # Duplicate
        {"regionName": "中部地區", "dataDate": "2026-04-14", "minT": 20.0, "maxT": 28.0},
    ])
    result = validate_weather_dataframe(df_dup)
    assert result.is_valid is False
    assert any("Duplicate record detected" in err for err in result.errors)
    assert result.valid_rows == 2  # Keeps one instance of (北部地區, 2026-04-14)
    assert result.dropped_rows == 1


def test_strict_mode_raises_exception():
    """Ensure strict=True raises WeatherValidationError immediately on failure."""
    bad_df = pd.DataFrame([
        {"regionName": "北部地區", "dataDate": "2026-04-14", "minT": 35.0, "maxT": 20.0}
    ])
    with pytest.raises(WeatherValidationError) as exc_info:
        validate_weather_dataframe(bad_df, strict=True)
    assert "Validation failed" in str(exc_info.value)


def test_is_valid_calendar_date_helper():
    """Test calendar date validator directly."""
    assert is_valid_calendar_date("2026-04-14") is True
    assert is_valid_calendar_date("2026-02-28") is True
    assert is_valid_calendar_date("2026-02-29") is False  # 2026 is not a leap year
    assert is_valid_calendar_date("2026-13-01") is False  # Invalid month
    assert is_valid_calendar_date(None) is False
