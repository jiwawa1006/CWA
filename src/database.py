import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data.db")

def get_connection():
    """"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    """"""

    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS WeatherObservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stationId TEXT NOT NULL,
        stationName TEXT,
        regionName TEXT NOT NULL,
        dataDate TEXT NOT NULL,
        weather TEXT,
        rainfall REAL,
        wind_dir REAL,
        wind_speed REAL,
        temp_c REAL,
        humidity REAL,
        pressure REAL,
        temp_max REAL,
        temp_min REAL,
        UNIQUE(stationId, dataDate)
    )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def insert_observations(df):
    """"""

    if df is None or df.empty:
        print("No data to insert.")
        return
        
    conn = get_connection()
    cursor = conn.cursor()

    cols = [
        "stationId", "stationName", "regionName", "dataDate",
        "weather", "rainfall", "wind_dir", "wind_speed",
        "temp_c", "humidity", "pressure", "temp_max", "temp_min"
    ]

    rows = (
        df[cols].astype(object).where(pd.notnull(df[cols]), None).values.tolist()
    )

    cursor.executemany("""
    INSERT OR REPLACE INTO WeatherObservations (
        stationId, stationName, regionName, dataDate,
        weather, rainfall, wind_dir, wind_speed,
        temp_c, humidity, pressure, temp_max, temp_min
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    
    conn.commit()
    conn.close()
    print(f"Successfully saved {len(rows)} weather observations.")

def is_empty() -> bool:
    """Return True when WeatherObservations doesn't exist or has no rows."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='WeatherObservations'"
        )
        if cursor.fetchone() is None:
            return True
        cursor.execute("SELECT COUNT(*) FROM WeatherObservations")
        return cursor.fetchone()[0] == 0
    finally:
        conn.close()


def get_all_regions():

    """"""

    conn = get_connection()
    query = """
        SELECT DISTINCT regionName
        FROM WeatherObservations
        ORDER BY regionName
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df["regionName"].tolist()

def get_observations_by_region(region_name):
    """"""

    conn = get_connection()
    query = """
        SELECT * FROM WeatherObservations
        WHERE regionName = ?
        ORDER BY dataDate
    """
    df = pd.read_sql_query(query, conn, params=(region_name,))
    conn.close()
    return df

def get_observation_by_date_range(start_date, end_date):
    """"""

    conn = get_connection()
    query = """
        SELECT * FROM WeatherObservations 
        WHERE dataDate >= ? AND dataDate <= ? 
        ORDER BY dataDate, regionName
    """
    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()
    return df

if __name__ == "__main__":
    print("Testing Database ...")
    init_db()
    
    try:
        from parse_weather import parse_weather_data
        df_weather = parse_weather_data()
        
        if df_weather is not None and not df_weather.empty:
            insert_observations(df_weather)
            
            regions = get_all_regions()
            print(f"\nRegions found in DB: {len(regions)}")
            if len(regions) > 0:
                print(f"Sample Regions: {regions[:5]}")
            
            if regions:
                sample_region = regions[0]
                print(f"\nObservations for '{sample_region}':")
                print(get_observations_by_region(sample_region))
    except ImportError:
        print("Could not import parse_weather_data. Make sure parse_weather.py is in the same directory.")
