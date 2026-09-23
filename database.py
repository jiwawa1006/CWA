"""database.py - SQLite Database Management for Taiwan Weather Forecast.

Will be implemented in Gate 5.
"""

import sqlite3
import pandas as pd

DB_PATH = "data.db"


def initialize_database(db_path: str = DB_PATH) -> None:
  """Initializes the SQLite database schema."""
  conn = sqlite3.connect(db_path)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS TemperatureForecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regionName TEXT NOT NULL,
            dataDate TEXT NOT NULL,
            minT REAL NOT NULL,
            maxT REAL NOT NULL,
            UNIQUE(regionName, dataDate)
        );
    """)
  conn.commit()
  conn.close()


def insert_forecasts(df: pd.DataFrame, db_path: str = DB_PATH) -> None:
  """Inserts forecast records into SQLite database."""
  pass


if __name__ == "__main__":
  initialize_database()
  print("Database initialized.")
