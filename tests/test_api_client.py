"""
test_api_client.py - Unit tests for CWA API configuration and client (Gate 1).
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import requests

from fetch_weather import (
    get_api_key,
    get_api_url,
    get_api_timeout,
    fetch_weather_raw,
    save_raw_weather,
    CWAMissingAPIKeyError,
    CWAAPIError,
    DEFAULT_API_URL,
    DEFAULT_TIMEOUT
)


def test_missing_api_key_raises_error(monkeypatch):
    """Ensure missing or empty CWA_API_KEY raises CWAMissingAPIKeyError."""
    monkeypatch.delenv("CWA_API_KEY", raising=False)
    with pytest.raises(CWAMissingAPIKeyError) as exc_info:
        get_api_key()
    assert "CWA_API_KEY environment variable is not set" in str(exc_info.value)


def test_get_api_key_success(monkeypatch):
    """Ensure valid CWA_API_KEY is retrieved correctly."""
    monkeypatch.setenv("CWA_API_KEY", "test-api-key-12345")
    assert get_api_key() == "test-api-key-12345"


def test_get_api_url_default(monkeypatch):
    """Ensure default API URL points to F-A0010-001 dataset."""
    monkeypatch.delenv("CWA_API_URL", raising=False)
    assert get_api_url() == DEFAULT_API_URL


def test_get_api_url_custom(monkeypatch):
    """Ensure custom CWA_API_URL override works."""
    custom_url = "https://custom.api.endpoint/test"
    monkeypatch.setenv("CWA_API_URL", custom_url)
    assert get_api_url() == custom_url


def test_get_api_timeout_configuration(monkeypatch):
    """Ensure timeout defaults properly and respects environment overrides."""
    monkeypatch.delenv("CWA_API_TIMEOUT", raising=False)
    assert get_api_timeout() == DEFAULT_TIMEOUT

    monkeypatch.setenv("CWA_API_TIMEOUT", "45")
    assert get_api_timeout() == 45

    monkeypatch.setenv("CWA_API_TIMEOUT", "not-a-number")
    assert get_api_timeout() == DEFAULT_TIMEOUT


@patch("requests.get")
def test_fetch_weather_raw_success(mock_get, monkeypatch):
    """Ensure successful HTTP 200 returns parsed dictionary."""
    monkeypatch.setenv("CWA_API_KEY", "dummy-key")
    sample_payload = {"success": "true", "records": {"locations": []}}
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sample_payload
    mock_get.return_value = mock_resp

    result = fetch_weather_raw()
    assert result == sample_payload
    mock_get.assert_called_once()
    
    # Verify Authorization header was passed
    args, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "dummy-key"


@patch("requests.get")
def test_fetch_weather_auth_error_401(mock_get, monkeypatch):
    """Ensure HTTP 401 Unauthorized raises CWAAPIError with helpful message."""
    monkeypatch.setenv("CWA_API_KEY", "invalid-key")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_get.return_value = mock_resp

    with pytest.raises(CWAAPIError) as exc_info:
        fetch_weather_raw()
    assert "Authentication failed" in str(exc_info.value)


@patch("requests.get")
def test_fetch_weather_timeout_error(mock_get, monkeypatch):
    """Ensure request timeout raises CWAAPIError."""
    monkeypatch.setenv("CWA_API_KEY", "dummy-key")
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    with pytest.raises(CWAAPIError) as exc_info:
        fetch_weather_raw(timeout=10)
    assert "timed out" in str(exc_info.value)


@patch("requests.get")
def test_fetch_weather_invalid_json(mock_get, monkeypatch):
    """Ensure non-JSON response raises CWAAPIError."""
    monkeypatch.setenv("CWA_API_KEY", "dummy-key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("No JSON object could be decoded")
    mock_get.return_value = mock_resp

    with pytest.raises(CWAAPIError) as exc_info:
        fetch_weather_raw()
    assert "Invalid JSON" in str(exc_info.value)


def test_save_raw_weather_creates_valid_file(tmp_path):
    """Ensure save_raw_weather writes JSON file correctly."""
    target_file = tmp_path / "subdir" / "weather_raw.json"
    dummy_data = {"test": 123, "locations": ["北部地區"]}

    saved_path = save_raw_weather(dummy_data, target_file)
    assert saved_path.exists()

    with open(saved_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == dummy_data
