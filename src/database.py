import sqlite3
import os
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    # check_same_thread=False allows Streamlit to share the connection across threads if needed
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """Initializes the database and creates the necessary tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create the table with a UNIQUE constraint to handle duplicate inserts gracefully
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS TemperatureForecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        regionName TEXT NOT NULL,
        dataDate TEXT NOT NULL,
        minT REAL,
        maxT REAL,
        rainfall REAL,
        humidity REAL,
        wind_speed REAL,
        wind_dir REAL,
        pressure REAL,
        temp_c REAL,
        UNIQUE(regionName, dataDate)
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def insert_forecasts(df):
    """
    Inserts a Pandas DataFrame of weather forecasts into the database.
    Uses 'INSERT OR REPLACE' to update existing records with the same region and date.
    """
    if df is None or df.empty:
        print("No data to insert.")
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Extract only the necessary columns and convert to list of tuples
    records = df[['regionName', 'dataDate', 'minT', 'maxT', 
                  'rainfall', 'humidity', 'wind_speed', 'wind_dir', 
                  'pressure', 'temp_c']].values.tolist()
    
    # Parameterized SQL for bulk insertion
    cursor.executemany('''
    INSERT OR REPLACE INTO TemperatureForecasts (regionName, dataDate, minT, maxT, rainfall, humidity, wind_speed, wind_dir, pressure, temp_c)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)
    
    conn.commit()
    conn.close()
    print(f"Successfully inserted/updated {len(records)} records in the database.")

def get_all_regions():
    """Returns a list of all unique region names in the database."""
    conn = get_connection()
    # Query only distinct regions to populate UI dropdowns
    df = pd.read_sql_query("SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName", conn)
    conn.close()
    return df['regionName'].tolist()

def get_forecast_by_region(region_name):
    """Returns the temperature forecasts for a specific region as a Pandas DataFrame."""
    conn = get_connection()
    # Parameterized SQL query to prevent SQL injection
    query = "SELECT * FROM TemperatureForecasts WHERE regionName = ? ORDER BY dataDate"
    df = pd.read_sql_query(query, conn, params=(region_name,))
    conn.close()
    return df

def get_forecast_by_date_range(start_date, end_date):
    """Returns the temperature forecasts within a specific date range."""
    conn = get_connection()
    query = "SELECT * FROM TemperatureForecasts WHERE dataDate >= ? AND dataDate <= ? ORDER BY dataDate, regionName"
    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()
    return df

if __name__ == "__main__":
    # Test and Validation block for Gate 3
    print("Testing Database Layer (Gate 3)...")
    init_db()
    
    try:
        # End-to-End Test: parse JSON -> DataFrame -> SQLite
        from parse_weather import parse_weather_data
        df_weather = parse_weather_data()
        
        if df_weather is not None and not df_weather.empty:
            insert_forecasts(df_weather)
            
            regions = get_all_regions()
            print(f"\nRegions found in DB: {len(regions)}")
            if len(regions) > 0:
                print(f"Sample Regions: {regions[:5]}")
            
            if regions:
                sample_region = regions[0]
                print(f"\nForecast for '{sample_region}':")
                print(get_forecast_by_region(sample_region))
    except ImportError:
        print("Could not import parse_weather_data. Make sure parse_weather.py is in the same directory.")
