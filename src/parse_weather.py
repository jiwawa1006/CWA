import os
import json
import pandas as pd

RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "weather_raw.json")

def _extract_obs_elements(station: dict) -> dict:
    """
    Return a dict of the observation elements we want from a single
    observation station.
    """
    we = station.get("WeatherElement", {})
    
    def safe_float(val):
        try:
            return float(val) if val not in ("", None, "-99", "-99.0", -99) else None
        except (ValueError, TypeError):
            return None

    rainfall = None
    if isinstance(we, dict) and "Now" in we and "Precipitation" in we["Now"]:
        rainfall = safe_float(we["Now"]["Precipitation"])

    return {
        "rainfall": rainfall,
        "humidity": safe_float(we.get("RelativeHumidity")) if isinstance(we, dict) else None,
        "wind_speed": safe_float(we.get("WindSpeed")) if isinstance(we, dict) else None,
        "wind_dir": safe_float(we.get("WindDirection")) if isinstance(we, dict) else None,
        "pressure": safe_float(we.get("AirPressure")) if isinstance(we, dict) else None,
        "temp_c": safe_float(we.get("AirTemperature")) if isinstance(we, dict) else None,
    }

def parse_weather_data(file_path=RAW_DATA_PATH):
    """
    Parses the raw JSON weather data and returns a cleaned Pandas DataFrame
    containing regionName, dataDate, minT, and maxT.
    """
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please run fetch_weather.py first.")
        return None
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    records = []
    
    try:
        # Check if the data is nested under 'records' -> 'locations' (7-day forecast)
        # or 'records' -> 'location' (observation data)
        # or 'records' -> 'Station' (new observation data format)
        if 'locations' in data.get('records', {}):
            locations = data['records']['locations'][0]['location']
            for loc in locations:
                region_name = loc['locationName']
                temp_by_date = {}
                
                # Find MinT and MaxT in weather elements
                for element in loc.get('weatherElement', []):
                    el_name = element.get('elementName')
                    
                    if el_name in ['MinT', 'MaxT']:
                        for time_period in element.get('time', []):
                            # Use startTime for the date (e.g., "2026-04-14 06:00:00")
                            start_time = time_period.get('startTime')
                            if not start_time:
                                continue
                                
                            date_str = start_time.split(" ")[0]
                            
                            # Extract the temperature value
                            try:
                                # Sometimes it's inside elementValue list
                                value = time_period['elementValue'][0]['value']
                            except (KeyError, IndexError):
                                # Other times it might be a direct key, adjust as needed
                                value = time_period.get('parameter', {}).get('parameterName', 0)
                                
                            if date_str not in temp_by_date:
                                temp_by_date[date_str] = {}
                                
                            try:
                                temp_by_date[date_str][el_name] = int(value)
                            except (ValueError, TypeError):
                                pass
                                
                # Construct the final records for this region
                for date_str, temps in temp_by_date.items():
                    if 'MinT' in temps and 'MaxT' in temps:
                        records.append({
                            'regionName': region_name,
                            'dataDate': date_str,
                            'minT': temps['MinT'],
                            'maxT': temps['MaxT']
                        })
                        
        elif 'Station' in data.get('records', {}):
            stations = data['records']['Station']
            for st in stations:
                try:
                    region_name = st['GeoInfo']['CountyName']
                    date_str = st['ObsTime']['DateTime'].split("T")[0]
                    min_t = float(st['WeatherElement']['DailyExtreme']['DailyLow']['TemperatureInfo']['AirTemperature'])
                    max_t = float(st['WeatherElement']['DailyExtreme']['DailyHigh']['TemperatureInfo']['AirTemperature'])
                    
                    # Ignore invalid extreme values like -99
                    if not (min_t > -50 and max_t > -50):
                        continue

                    # Pull extra observation elements
                    extra = _extract_obs_elements(st)

                    record = {
                        'regionName': region_name,
                        'dataDate': date_str,
                        'minT': min_t,
                        'maxT': max_t,
                        **extra
                    }
                    records.append(record)
                except (KeyError, ValueError, TypeError):
                    pass
        else:
            raise KeyError("Neither 'locations' nor 'Station' found in 'records'")
                    
        df = pd.DataFrame(records)
        return df
        
    except Exception as e:
        print(f"Parsing error: The JSON structure doesn't match the expected F-A0010-001 format.")
        print(f"Details: {e}")
        print("Note: If you are using API O-A0001-001 (Observation data), it does not provide 7-day forecast MinT/MaxT.")
        return None

if __name__ == "__main__":
    print("Parsing weather data...")
    df = parse_weather_data()
    if df is not None and not df.empty:
        print("\nParsing Successful! Here is a sample of the data:")
        print(df.head(15))
        print(f"\nTotal records extracted: {len(df)}")
    elif df is not None and df.empty:
         print("Parsing completed, but no MinT/MaxT records were found in the JSON.")
