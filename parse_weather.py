"""parse_weather.py - Parser for CWA Weather Forecast JSON.

Will be implemented in Gate 3.
"""

import pandas as pd


def parse_weather_data(data: dict) -> pd.DataFrame:
  """Parses raw CWA weather forecast JSON data into a normalized DataFrame."""
  # Placeholder for Gate 0
  return pd.DataFrame(columns=["regionName", "dataDate", "minT", "maxT"])


if __name__ == "__main__":
  print("Parser module placeholder.")
