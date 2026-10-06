import os
import json
import requests

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path)

API_PATH = os.environ.get("CWA_API")
API_URL = f"https://opendata.cwa.gov.tw{API_PATH}"
RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "weather_raw.json")

def fetch_weather_data():
    """"""

    api_key = os.getenv("CWA_API_KEY")
    
    if not api_key:
        print("Error: CWA_API_KEY is not set")
        print("Please configure your API key in the .env file.")
        return False
        
    headers = {
        "Authorization": api_key
    }
    
    print(f"Fetching data from {API_URL}...")
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(API_URL, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        data = response.json()
        success = data.get("success")
        
        if success == "true":
            print("Data fetched successfully!")
            os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
            with open(RAW_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
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
