"""
test_parser.py - Unit tests for Gate 3: JSON Parsing and Data Normalization.
"""

import json
import re
from pathlib import Path
import pandas as pd
import pytest

from parse_weather import (
    parse_weather_data,
    normalize_date,
    to_float,
    REQUIRED_COLUMNS
)

SAMPLE_FILE = Path(__file__).parent / "sample_weather.json"


def test_sample_json_exists():
    """Verify that sample_weather.json is present and valid."""
    assert SAMPLE_FILE.exists()
    with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["success"] == "true"
    assert "records" in data


def test_parser_produces_dataframe():
    """Verify that parse_weather_data returns a pandas DataFrame."""
    df = parse_weather_data(SAMPLE_FILE)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_required_columns_exist():
    """Verify that all required columns are present in DataFrame."""
    df = parse_weather_data(SAMPLE_FILE)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns


def test_dates_are_normalized():
    """Verify that dates follow standard YYYY-MM-DD format."""
    df = parse_weather_data(SAMPLE_FILE)
    date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for date_val in df["dataDate"]:
        assert date_regex.match(str(date_val))


def test_mint_maxt_are_numeric():
    """Verify that minT and maxT are numeric (float)."""
    df = parse_weather_data(SAMPLE_FILE)
    assert pd.api.types.is_numeric_dtype(df["minT"])
    assert pd.api.types.is_numeric_dtype(df["maxT"])
    assert not df["minT"].isna().any()
    assert not df["maxT"].isna().any()


def test_multiple_regions_parsed():
    """Verify that multiple regions are parsed from sample data."""
    df = parse_weather_data(SAMPLE_FILE)
    regions = df["regionName"].unique()
    assert len(regions) >= 2
    assert "北部地區" in regions
    assert "中部地區" in regions


def test_multiple_forecast_days_parsed():
    """Verify that multiple forecast days are parsed."""
    df = parse_weather_data(SAMPLE_FILE)
    dates = df["dataDate"].unique()
    assert len(dates) >= 2


def test_missing_data_does_not_crash():
    """Verify parser robustness against empty, malformed, or incomplete data."""
    # Empty inputs
    assert parse_weather_data({}).empty
    assert parse_weather_data(None).empty
    assert parse_weather_data("invalid-json-string").empty

    # Incomplete records
    incomplete_json = {
        "success": "true",
        "records": {
            "locations": [
                {
                    "location": [
                        {"locationName": "測試地區", "weatherElement": []},
                        {"locationName": "", "weatherElement": [{"elementName": "MinT"}]},
                        {"locationName": "未知", "weatherElement": [{"elementName": "MinT", "time": [{"startTime": "bad-date", "elementValue": [{"value": "NaN"}]}]}]}
                    ]
                }
            ]
        }
    }
    df = parse_weather_data(incomplete_json)
    assert isinstance(df, pd.DataFrame)
    assert set(df.columns) == set(REQUIRED_COLUMNS)


def test_to_float_and_normalize_date_helpers():
    """Test helper functions directly for edge cases."""
    assert to_float("23.5") == 23.5
    assert to_float("-99") is None  # Sentinel
    assert to_float("invalid") is None
    assert to_float(None) is None

    assert normalize_date("2026-04-14 06:00:00") == "2026-04-14"
    assert normalize_date("2026-04-14T12:00:00+08:00") == "2026-04-14"
    assert normalize_date("invalid") is None
    assert normalize_date(None) is None


def test_station_observation_parsing():
    """Verify parser works on CWA Station observation schema (O-A0003-001)."""
    obs_json = {
        "success": "true",
        "records": {
            "Station": [
                {
                    "StationName": "臺北",
                    "GeoInfo": {"CountyName": "臺北市"},
                    "ObsTime": {"DateTime": "2026-09-23T11:00:00+08:00"},
                    "WeatherElement": {
                        "AirTemperature": "28.5",
                        "DailyExtreme": {
                            "DailyHigh": {"TemperatureInfo": {"AirTemperature": "32.0"}},
                            "DailyLow": {"TemperatureInfo": {"AirTemperature": "24.0"}}
                        }
                    }
                },
                {
                    "StationName": "臺中",
                    "GeoInfo": {"CountyName": "臺中市"},
                    "ObsTime": {"DateTime": "2026-09-23T11:00:00+08:00"},
                    "WeatherElement": {
                        "AirTemperature": "29.0",
                        "DailyExtreme": {
                            "DailyHigh": {"TemperatureInfo": {"AirTemperature": "33.0"}},
                            "DailyLow": {"TemperatureInfo": {"AirTemperature": "22.5"}}
                        }
                    }
                }
            ]
        }
    }
    df = parse_weather_data(obs_json)
    assert not df.empty
    assert "北部地區" in df["regionName"].values
    assert "中部地區" in df["regionName"].values
    assert df["dataDate"].iloc[0] == "2026-09-23"
