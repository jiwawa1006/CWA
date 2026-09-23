"""
test_raw_data.py - Unit and integration tests for Gate 2: Raw Weather Data Acquisition.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from fetch_weather import (
    fetch_weather_raw,
    save_raw_weather,
    fetch_and_save_weather,
    CWAAPIError
)


def test_fetch_and_save_weather_success(tmp_path, monkeypatch):
    """Ensure fetch_and_save_weather fetches, saves to file, and returns data."""
    monkeypatch.setenv("CWA_API_KEY", "dummy-secret-key-999")
    mock_payload = {
        "success": "true",
        "records": {
            "Station": [
                {
                    "StationName": "基隆",
                    "StationId": "466940",
                    "WeatherElement": {"AirTemperature": "24.5"}
                }
            ]
        }
    }

    target_file = tmp_path / "data" / "weather_raw.json"

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        returned_data = fetch_and_save_weather(filepath=target_file)

    assert returned_data == mock_payload
    assert target_file.exists()

    with open(target_file, "r", encoding="utf-8") as f:
        saved_json = json.load(f)

    assert saved_json == mock_payload
    assert len(saved_json["records"]["Station"]) == 1


def test_raw_data_does_not_contain_api_key(tmp_path, monkeypatch):
    """Ensure the API Key is never written into the raw data file."""
    secret_key = "CWA-SECRET-AUTH-TOKEN-12345"
    monkeypatch.setenv("CWA_API_KEY", secret_key)
    
    mock_payload = {
        "success": "true",
        "records": {"Station": [{"StationName": "臺北"}]}
    }
    target_file = tmp_path / "data" / "weather_raw.json"

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload
        mock_get.return_value = mock_resp

        fetch_and_save_weather(filepath=target_file)

    raw_text = target_file.read_text(encoding="utf-8")
    assert secret_key not in raw_text


def test_fetch_and_save_weather_handles_error(tmp_path, monkeypatch):
    """Ensure errors during fetch prevent corrupted writes."""
    monkeypatch.setenv("CWA_API_KEY", "dummy-key")
    target_file = tmp_path / "data" / "weather_raw.json"

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_get.return_value = mock_resp

        with pytest.raises(CWAAPIError):
            fetch_and_save_weather(filepath=target_file)

    assert not target_file.exists()
