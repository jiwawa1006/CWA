import os
import json
import pandas as pd

RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "weather_raw.json")

def _extract_obs_elements(station: dict) -> dict:
    """"""

    we = station.get("WeatherElement", {})
    def to_float(val):
        try:
            number = float(val)
            return number if number != -99 else None
        except (ValueError, TypeError):
            return None

    return {
        "weather": we.get("Weather"),
        "rainfall": to_float(we.get("Now", {}).get("Precipitation")),
        "wind_dir": to_float(we.get("WindDirection")),
        "wind_speed": to_float(we.get("WindSpeed")),
        "temp_c": to_float(we.get("AirTemperature")),
        "humidity": to_float(we.get("RelativeHumidity")),
        "pressure": to_float(we.get("AirPressure")),
        "temp_min": to_float(we.get("DailyExtreme", {}).get("DailyLow", {}).get("TemperatureInfo", {}).get("AirTemperature")),
        "temp_max": to_float(we.get("DailyExtreme", {}).get("DailyHigh", {}).get("TemperatureInfo", {}).get("AirTemperature")),
    }

def parse_weather_data(file_path=RAW_DATA_PATH):
    """"""

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please run fetch_weather.py first.")
        return None
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = []
    stations = data.get("records", {}).get("Station", [])
    if not stations:
        print("No station records found in the CWA response.")
        return pd.DataFrame()

    for st in stations:
        try:
            station_name = st["StationName"]
            station_id = st["StationId"]
            region_name = st["GeoInfo"]["CountyName"]
            date_str = st["ObsTime"]["DateTime"]
            extra = _extract_obs_elements(st)

            records.append({
                "stationName": station_name,
                "stationId": station_id,
                "regionName": region_name,
                "dataDate": date_str,
                **extra
            })
        except (KeyError, TypeError) as e:
            print(f"Skipping station record with missing or invalid fields: {e}")

    return pd.DataFrame(records)

if __name__ == "__main__":
    print("Parsing weather data...")
    df = parse_weather_data()
    if df is not None and not df.empty:
        print("\nParsing Successful! Here is a sample of the data:")
        print(df.head(15))
        print(f"\nTotal records extracted: {len(df)}")
    else:
        print("Parsing failed")
