"""
database.py - SQLite Database Management for Taiwan Weather Forecast.

Provides relational storage, upsert mechanisms, and query abstractions
for regional temperature forecasts and observations.
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import List, Optional, Generator
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data.db"


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for SQLite database connection.
    Ensures proper transaction commit, rollback on failure, and connection closure.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Initializes SQLite database and creates the TemperatureForecasts table if not exists.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS TemperatureForecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                regionName TEXT NOT NULL,
                dataDate TEXT NOT NULL,
                minT REAL,
                maxT REAL,
                UNIQUE(regionName, dataDate)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_region_date 
            ON TemperatureForecasts(regionName, dataDate);
        """)
    logger.info(f"Database initialized at '{db_path}'.")


def upsert_forecasts(df: pd.DataFrame, db_path: str = DEFAULT_DB_PATH) -> int:
    """
    Inserts or updates forecast records in TemperatureForecasts table using parameterized queries.
    Handles duplicate (regionName, dataDate) records by updating minT and maxT values.

    Returns:
        Number of rows processed.
    """
    if df is None or df.empty:
        logger.info("No data provided to upsert into database.")
        return 0

    initialize_database(db_path)

    required_cols = ["regionName", "dataDate", "minT", "maxT"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"DataFrame must contain column '{col}' for insertion.")

    rows_to_insert = []
    for _, row in df.iterrows():
        region = str(row["regionName"]).strip()
        date_val = str(row["dataDate"]).strip()
        min_t = float(row["minT"]) if pd.notna(row["minT"]) and row["minT"] is not None else None
        max_t = float(row["maxT"]) if pd.notna(row["maxT"]) and row["maxT"] is not None else None
        if region and date_val:
            rows_to_insert.append((region, date_val, min_t, max_t))

    if not rows_to_insert:
        return 0

    query = """
        INSERT INTO TemperatureForecasts (regionName, dataDate, minT, maxT)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(regionName, dataDate) DO UPDATE SET
            minT = excluded.minT,
            maxT = excluded.maxT;
    """

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(query, rows_to_insert)
        affected = len(rows_to_insert)

    logger.info(f"Upserted {affected} forecast records into '{db_path}'.")
    return affected


def insert_forecasts(df: pd.DataFrame, db_path: str = DEFAULT_DB_PATH) -> int:
    """Alias for upsert_forecasts to satisfy Gate 5 requirements."""
    return upsert_forecasts(df, db_path=db_path)


def get_regions(db_path: str = DEFAULT_DB_PATH) -> List[str]:
    """Retrieves a sorted list of distinct region names stored in the database."""
    initialize_database(db_path)
    query = "SELECT DISTINCT regionName FROM TemperatureForecasts ORDER BY regionName ASC;"
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
    return [row["regionName"] for row in rows]


def get_forecast(region: str, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """
    Queries forecast records for a specific region, sorted by dataDate ascending.
    Uses parameterized SQL to prevent SQL injection.
    """
    initialize_database(db_path)
    query = """
        SELECT regionName, dataDate, minT, maxT
        FROM TemperatureForecasts
        WHERE regionName = ?
        ORDER BY dataDate ASC;
    """
    with get_connection(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=(region,))
    return df


def get_all_forecasts(db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """Queries all records in TemperatureForecasts, sorted by dataDate and regionName."""
    initialize_database(db_path)
    query = """
        SELECT regionName, dataDate, minT, maxT
        FROM TemperatureForecasts
        ORDER BY dataDate ASC, regionName ASC;
    """
    with get_connection(db_path) as conn:
        df = pd.read_sql_query(query, conn)
    return df


def clear_forecasts(db_path: str = DEFAULT_DB_PATH) -> int:
    """Clears all records from the TemperatureForecasts table."""
    initialize_database(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM TemperatureForecasts;")
        count = cursor.rowcount
    logger.info(f"Cleared {count} records from '{db_path}'.")
    return count


if __name__ == "__main__":
    from parse_weather import parse_weather_data
    from validate_weather import validate_weather_dataframe

    sample_json = Path("tests/sample_weather.json")
    if sample_json.exists():
        raw_df = parse_weather_data(sample_json)
        val = validate_weather_dataframe(raw_df)
        insert_forecasts(val.validated_df)
        print("Inserted sample data into data.db.")
        print("Available regions in DB:", get_regions())
        for r in get_regions():
            print(f"\nForecast for {r}:")
            print(get_forecast(r))
