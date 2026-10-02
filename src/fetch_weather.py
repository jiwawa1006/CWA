import os
import json
import requests
# Manually load environment variables from .env file to avoid external dependencies
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")
                except ValueError:
                    pass

# Get the API path from .env, or default to F-A0010-001 (7-day forecast)
API_PATH = os.environ.get("CWA_API", "/api/v1/rest/datastore/F-A0010-001")
if API_PATH.startswith("http"):
    API_URL = API_PATH
else:
    API_URL = f"https://opendata.cwa.gov.tw{API_PATH}"
RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "weather_raw.json")

def fetch_weather_data():
    """Fetches weather data from CWA API and saves it locally."""
    api_key = os.getenv("CWA_API_KEY")
    
    if not api_key or api_key == "your_api_key_here":
        print("Error: CWA_API_KEY is not set or is using the default placeholder.")
        print("Please configure your API key in the .env file or environment variable.")
        return False
        
    headers = {
        "Authorization": api_key
    }
    
    print(f"Fetching data from {API_URL}...")
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(API_URL, headers=headers, timeout=30, verify=False)
        
        # Raise HTTPError for bad responses (4xx or 5xx)
        response.raise_for_status()
        
        data = response.json()
        
        # Verify the success field in the response (based on typical CWA API format)
        if data.get("success") == "true":
            print("Data fetched successfully!")
            
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
            
            # Save the raw JSON data
            with open(RAW_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            print(f"Raw data saved to {RAW_DATA_PATH}")
            return True
        else:
            print(f"API Error: {data}")
            return False
            
    except requests.exceptions.Timeout:
        print("Error: The request timed out. Please try again later.")
        return False
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP Error: {errh}")
        return False
    except requests.exceptions.ConnectionError as errc:
        print(f"Error Connecting: {errc}")
        return False
    except requests.exceptions.RequestException as err:
        print(f"Error: An unexpected error occurred: {err}")
        return False

if __name__ == "__main__":
    fetch_weather_data()
