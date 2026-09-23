"""
fetch_weather.py - CWA Open Data API Client and Acquisition Module.

Handles API configuration, authentication, HTTP requests with timeouts and error handling.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import requests

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if available
    load_dotenv()
except ImportError:
    pass

# Setup logging without exposing sensitive data
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants & Default Configurations
DEFAULT_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"
DEFAULT_TIMEOUT = 30
DATA_DIR = Path(__file__).parent / "data"
RAW_DATA_FILE = DATA_DIR / "weather_raw.json"


class CWAAPIError(Exception):
    """Custom exception for CWA API errors."""
    pass


class CWAMissingAPIKeyError(CWAAPIError):
    """Raised when CWA_API_KEY is not configured."""
    pass


def get_api_key() -> str:
    """
    Retrieves the CWA API key from the environment.
    
    Raises:
        CWAMissingAPIKeyError: If CWA_API_KEY is missing or empty.
    """
    api_key = os.getenv("CWA_API_KEY")
    if not api_key or not api_key.strip():
        raise CWAMissingAPIKeyError(
            "CWA_API_KEY environment variable is not set. "
            "Please set CWA_API_KEY in your environment or in a .env file."
        )
    return api_key.strip()


def get_api_url() -> str:
    """Retrieves the CWA API URL from environment or uses default."""
    return os.getenv("CWA_API_URL", DEFAULT_API_URL).strip()


def get_api_timeout() -> int:
    """Retrieves the request timeout in seconds."""
    timeout_val = os.getenv("CWA_API_TIMEOUT")
    if timeout_val:
        try:
            return int(timeout_val)
        except ValueError:
            logger.warning(
                f"Invalid CWA_API_TIMEOUT value '{timeout_val}', defaulting to {DEFAULT_TIMEOUT}s."
            )
    return DEFAULT_TIMEOUT


def fetch_weather_raw(
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetches raw 7-day weather forecast from CWA Open Data API.
    
    Args:
        api_key: Optional API key override. If None, loaded from environment.
        api_url: Optional API URL override. If None, loaded from environment.
        timeout: Optional timeout in seconds. If None, loaded from environment.
        
    Returns:
        Parsed JSON dictionary containing the API response.
        
    Raises:
        CWAMissingAPIKeyError: If API key is not configured.
        CWAAPIError: On network, HTTP, or JSON parsing errors.
    """
    key = api_key or get_api_key()
    url = api_url or get_api_url()
    req_timeout = timeout or get_api_timeout()

    logger.info(f"Connecting to CWA API at {url} (Timeout: {req_timeout}s)...")

    headers = {
        "Authorization": key,
        "Accept": "application/json",
        "User-Agent": "AIoT-CWA-WeatherApp/1.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=req_timeout)
    except requests.exceptions.Timeout as e:
        logger.error("Request to CWA API timed out.")
        raise CWAAPIError(f"Request to CWA API timed out after {req_timeout} seconds.") from e
    except requests.exceptions.ConnectionError as e:
        logger.error("Failed to connect to CWA API.")
        raise CWAAPIError("Network connection error while connecting to CWA API.") from e
    except requests.exceptions.RequestException as e:
        logger.error("Unexpected error during CWA API request.")
        raise CWAAPIError(f"CWA API request failed: {e}") from e

    if response.status_code in (401, 403):
        logger.error(f"Authentication failed: HTTP {response.status_code}.")
        raise CWAAPIError(
            f"Authentication failed (HTTP {response.status_code}). Please verify your CWA_API_KEY."
        )
    elif response.status_code != 200:
        logger.error(f"CWA API returned error status HTTP {response.status_code}.")
        raise CWAAPIError(
            f"CWA API returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        data = response.json()
    except ValueError as e:
        logger.error("Failed to parse response body as JSON.")
        raise CWAAPIError("Invalid JSON received from CWA API.") from e

    if not isinstance(data, dict):
        raise CWAAPIError("Expected JSON object from CWA API, got different type.")

    if "success" in data and str(data["success"]).lower() != "true":
        msg = data.get("message", "API response indicated failure")
        logger.error(f"CWA API indicated failure: {msg}")
        raise CWAAPIError(f"CWA API error: {msg}")

    return data


def save_raw_weather(data: Dict[str, Any], filepath: Path = RAW_DATA_FILE) -> Path:
    """
    Saves raw JSON response to file.
    Ensures directory exists and file is valid JSON.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Raw weather data saved to {filepath}")
    return filepath


def fetch_and_save_weather(
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    timeout: Optional[int] = None,
    filepath: Path = RAW_DATA_FILE
) -> Dict[str, Any]:
    """
    Convenience function that fetches weather data from CWA API,
    saves the raw JSON to disk, and returns the parsed JSON object.
    """
    data = fetch_weather_raw(api_key=api_key, api_url=api_url, timeout=timeout)
    save_raw_weather(data, filepath=filepath)
    return data


def main():
    """CLI entry point for fetch_weather."""
    try:
        fetch_and_save_weather()
        print("Successfully fetched and saved raw weather forecast data.")
    except CWAMissingAPIKeyError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except CWAAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
