"""
parse_weather.py - Parser and Normalizer for CWA Weather Forecast and Observation JSON.

Converts nested CWA JSON structures into a clean, normalized Pandas DataFrame.
Supports both Forecast (e.g. F-A0010-001, F-C0032-001) and Observation (O-A0003-001) schemas.
"""

import re
import json
import logging
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)

# Standard columns required by the project schema
REQUIRED_COLUMNS = ["regionName", "dataDate", "minT", "maxT"]

# Mapping from Taiwan County to Major Geographical Regions
COUNTY_TO_REGION = {
    "基隆市": "北部地區",
    "臺北市": "北部地區",
    "台北市": "北部地區",
    "新北市": "北部地區",
    "桃園市": "北部地區",
    "新竹市": "北部地區",
    "新竹縣": "北部地區",
    "苗栗縣": "北部地區",
    "臺中市": "中部地區",
    "台中市": "中部地區",
    "彰化縣": "中部地區",
    "南投縣": "中部地區",
    "雲林縣": "中部地區",
    "嘉義市": "中部地區",
    "嘉義縣": "中部地區",
    "臺南市": "南部地區",
    "台南市": "南部地區",
    "高雄市": "南部地區",
    "屏東縣": "南部地區",
    "宜蘭縣": "東北部地區",
    "花蓮縣": "東部地區",
    "臺東縣": "東南部地區",
    "台東縣": "東南部地區",
    "澎湖縣": "澎湖地區",
    "金門縣": "金門地區",
    "連江縣": "馬祖地區",
}


def normalize_date(date_str: Any) -> Optional[str]:
    """
    Normalizes a date string to YYYY-MM-DD format.
    Accepts formats such as:
      - 2026-04-14 06:00:00
      - 2026-04-14T06:00:00+08:00
      - 2026/04/14
    """
    if not date_str or not isinstance(date_str, str):
        return None
    match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", date_str)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return None


def to_float(val: Any) -> Optional[float]:
    """Safely converts value to float, ignoring sensor error sentinels like -99."""
    if val is None:
        return None
    try:
        f = float(val)
        if f < -50 or f > 60:
            return None
        return f
    except (ValueError, TypeError):
        return None


def extract_temp_from_time_item(time_item: Dict[str, Any]) -> Optional[float]:
    """Extracts temperature numeric value from a weather element time entry."""
    if not isinstance(time_item, dict):
        return None

    # Case 1: elementValue list
    elem_val = time_item.get("elementValue")
    if isinstance(elem_val, list) and len(elem_val) > 0:
        first = elem_val[0]
        if isinstance(first, dict):
            return to_float(first.get("value"))
        return to_float(first)
    elif isinstance(elem_val, dict):
        return to_float(elem_val.get("value"))

    # Case 2: parameter dict (e.g. parameterName)
    param = time_item.get("parameter")
    if isinstance(param, dict):
        return to_float(param.get("parameterName"))

    # Case 3: direct value field
    if "value" in time_item:
        return to_float(time_item.get("value"))

    return None


def parse_forecast_records(records: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parses records conforming to CWA forecast formats (locations / location list)."""
    rows = []
    if not isinstance(records, dict):
        return rows

    # Traverse records -> locations -> location
    location_list = []
    if "locations" in records:
        locations_wrapper = records["locations"]
        if isinstance(locations_wrapper, list):
            for loc_group in locations_wrapper:
                if isinstance(loc_group, dict) and "location" in loc_group:
                    location_list.extend(loc_group.get("location", []))
        elif isinstance(locations_wrapper, dict) and "location" in locations_wrapper:
            location_list.extend(locations_wrapper.get("location", []))
    elif "location" in records:
        locs = records.get("location")
        if isinstance(locs, list):
            location_list.extend(locs)

    for loc in location_list:
        if not isinstance(loc, dict):
            continue

        region_name = loc.get("locationName")
        if not region_name or not str(region_name).strip():
            continue
        region_name = str(region_name).strip()

        weather_elements = loc.get("weatherElement", [])
        if not isinstance(weather_elements, list):
            continue

        # Map dates to minT and maxT
        date_temps = defaultdict(lambda: {"minT": None, "maxT": None})

        for elem in weather_elements:
            if not isinstance(elem, dict):
                continue
            elem_name = elem.get("elementName", "")
            times = elem.get("time", [])
            if not isinstance(times, list):
                continue

            if elem_name == "MinT":
                for t in times:
                    date_str = normalize_date(t.get("startTime") or t.get("dataTime") or t.get("endTime"))
                    temp_val = extract_temp_from_time_item(t)
                    if date_str and temp_val is not None:
                        cur = date_temps[date_str]["minT"]
                        date_temps[date_str]["minT"] = temp_val if cur is None else min(cur, temp_val)

            elif elem_name == "MaxT":
                for t in times:
                    date_str = normalize_date(t.get("startTime") or t.get("dataTime") or t.get("endTime"))
                    temp_val = extract_temp_from_time_item(t)
                    if date_str and temp_val is not None:
                        cur = date_temps[date_str]["maxT"]
                        date_temps[date_str]["maxT"] = temp_val if cur is None else max(cur, temp_val)

        for data_date, temps in sorted(date_temps.items()):
            min_t = temps["minT"]
            max_t = temps["maxT"]

            if min_t is not None or max_t is not None:
                if min_t is None and max_t is not None:
                    min_t = max_t
                elif max_t is None and min_t is not None:
                    max_t = min_t

                rows.append({
                    "regionName": region_name,
                    "dataDate": data_date,
                    "minT": float(min_t),
                    "maxT": float(max_t)
                })

    return rows


def parse_station_observation_records(records: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parses records conforming to CWA Station observations (O-A0003-001)."""
    rows = []
    if not isinstance(records, dict):
        return rows

    stations = records.get("Station", [])
    if not isinstance(stations, list):
        return rows

    region_date_data = defaultdict(lambda: {"mins": [], "maxs": []})

    for st in stations:
        if not isinstance(st, dict):
            continue

        geo_info = st.get("GeoInfo", {})
        county = geo_info.get("CountyName") if isinstance(geo_info, dict) else st.get("CountyName")
        region_name = COUNTY_TO_REGION.get(county) or county or st.get("StationName") or "其他地區"

        obs_time = st.get("ObsTime", {})
        date_raw = obs_time.get("DateTime") if isinstance(obs_time, dict) else st.get("ObsTime")
        data_date = normalize_date(date_raw)
        if not data_date:
            continue

        elem = st.get("WeatherElement", {})
        if not isinstance(elem, dict):
            continue

        daily_extreme = elem.get("DailyExtreme", {})
        daily_high = None
        daily_low = None

        if isinstance(daily_extreme, dict):
            high_info = daily_extreme.get("DailyHigh", {}).get("TemperatureInfo", {})
            low_info = daily_extreme.get("DailyLow", {}).get("TemperatureInfo", {})
            daily_high = to_float(high_info.get("AirTemperature"))
            daily_low = to_float(low_info.get("AirTemperature"))

        current_temp = to_float(elem.get("AirTemperature"))

        station_min = daily_low if daily_low is not None else current_temp
        station_max = daily_high if daily_high is not None else current_temp

        if station_min is not None:
            region_date_data[(region_name, data_date)]["mins"].append(station_min)
        if station_max is not None:
            region_date_data[(region_name, data_date)]["maxs"].append(station_max)

    for (region_name, data_date), values in sorted(region_date_data.items()):
        mins = values["mins"]
        maxs = values["maxs"]
        if mins and maxs:
            rows.append({
                "regionName": region_name,
                "dataDate": data_date,
                "minT": round(min(mins), 1),
                "maxT": round(max(maxs), 1)
            })
        elif mins:
            val = round(sum(mins) / len(mins), 1)
            rows.append({
                "regionName": region_name,
                "dataDate": data_date,
                "minT": val,
                "maxT": val
            })

    return rows


def parse_weather_data(data: Union[Dict[str, Any], str, Path]) -> pd.DataFrame:
    """
    Main entry point to parse weather JSON data into a normalized DataFrame.

    Args:
        data: Can be a parsed dict, a JSON string, or a Path/filepath to a JSON file.

    Returns:
        Pandas DataFrame with columns: ['regionName', 'dataDate', 'minT', 'maxT']
    """
    if isinstance(data, (str, Path)):
        path = Path(data)
        if path.exists() and path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        elif isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                logger.error("Failed to parse provided string as JSON.")
                return pd.DataFrame(columns=REQUIRED_COLUMNS)

    if not isinstance(data, dict):
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    records = data.get("records")
    if not isinstance(records, dict):
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    if "Station" in records:
        rows = parse_station_observation_records(records)
    else:
        rows = parse_forecast_records(records)

    df = pd.DataFrame(rows, columns=REQUIRED_COLUMNS)

    if not df.empty:
        df["minT"] = pd.to_numeric(df["minT"], errors="coerce")
        df["maxT"] = pd.to_numeric(df["maxT"], errors="coerce")
        df = df.dropna(subset=["regionName", "dataDate", "minT", "maxT"])
        df = df.sort_values(by=["regionName", "dataDate"]).reset_index(drop=True)

    return df


if __name__ == "__main__":
    raw_path = Path("data/weather_raw.json")
    if raw_path.exists():
        df = parse_weather_data(raw_path)
        print("Parsed DataFrame from data/weather_raw.json:")
        print(df)
        print(f"Total rows: {len(df)}")
    else:
        sample_path = Path("tests/sample_weather.json")
        df = parse_weather_data(sample_path)
        print("Parsed DataFrame from tests/sample_weather.json:")
        print(df)
