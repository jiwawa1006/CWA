"""
test_database.py - Unit tests for Gate 5: SQLite Database Layer.
"""

import os
import pytest
import pandas as pd
from pathlib import Path

from database import (
    initialize_database,
    insert_forecasts,
    upsert_forecasts,
    get_regions,
    get_forecast,
    get_all_forecasts,
    clear_forecasts
)


@pytest.fixture
def test_db(tmp_path):
    """Provide a temporary database path for isolated tests."""
    db_path = str(tmp_path / "test.db")
    initialize_database(db_path)
    return db_path


@pytest.fixture
def sample_df():
    """Provide a valid sample DataFrame."""
    return pd.DataFrame([
        {"regionName": "北部地區", "dataDate": "2026-04-14", "minT": 18.0, "maxT": 26.0},
        {"regionName": "北部地區", "dataDate": "2026-04-15", "minT": 19.0, "maxT": 27.0},
        {"regionName": "中部地區", "dataDate": "2026-04-14", "minT": 20.0, "maxT": 30.0},
        {"regionName": "南部地區", "dataDate": "2026-04-14", "minT": 22.0, "maxT": 31.0},
    ])


def test_database_created_automatically(tmp_path):
    """Verify database file is created when initialize_database is called."""
    db_path = str(tmp_path / "auto.db")
    assert not Path(db_path).exists()
    initialize_database(db_path)
    assert Path(db_path).exists()


def test_table_created_automatically(test_db):
    """Verify TemperatureForecasts table exists after initialization."""
    import sqlite3
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='TemperatureForecasts';")
    result = cursor.fetchone()
    conn.close()
    assert result is not None
    assert result[0] == "TemperatureForecasts"


def test_insert_valid_data(test_db, sample_df):
    """Verify valid forecast data can be inserted successfully."""
    count = insert_forecasts(sample_df, db_path=test_db)
    assert count == 4

    regions = get_regions(db_path=test_db)
    assert len(regions) == 3
    assert "北部地區" in regions
    assert "中部地區" in regions
    assert "南部地區" in regions


def test_duplicate_region_date_handled(test_db, sample_df):
    """Verify duplicate (regionName, dataDate) records are upserted, not duplicated."""
    insert_forecasts(sample_df, db_path=test_db)

    updated_df = pd.DataFrame([
        {"regionName": "北部地區", "dataDate": "2026-04-14", "minT": 17.0, "maxT": 28.0},
    ])
    insert_forecasts(updated_df, db_path=test_db)

    result = get_forecast("北部地區", db_path=test_db)
    row_apr14 = result[result["dataDate"] == "2026-04-14"]
    assert len(row_apr14) == 1  # No duplicate
    assert row_apr14.iloc[0]["minT"] == 17.0  # Updated value
    assert row_apr14.iloc[0]["maxT"] == 28.0  # Updated value


def test_get_regions(test_db, sample_df):
    """Verify get_regions returns sorted distinct region names."""
    insert_forecasts(sample_df, db_path=test_db)
    regions = get_regions(db_path=test_db)
    assert regions == sorted(regions)
    assert len(set(regions)) == len(regions)  # All unique


def test_get_forecast_by_region(test_db, sample_df):
    """Verify get_forecast returns correct data for a selected region."""
    insert_forecasts(sample_df, db_path=test_db)
    df = get_forecast("北部地區", db_path=test_db)
    assert len(df) == 2
    assert list(df.columns) == ["regionName", "dataDate", "minT", "maxT"]
    assert df.iloc[0]["dataDate"] <= df.iloc[1]["dataDate"]  # Sorted by date


def test_get_forecast_nonexistent_region(test_db, sample_df):
    """Verify querying a nonexistent region returns empty DataFrame."""
    insert_forecasts(sample_df, db_path=test_db)
    df = get_forecast("不存在地區", db_path=test_db)
    assert len(df) == 0


def test_parameterized_sql_injection_safe(test_db, sample_df):
    """Verify SQL injection via region name is safely handled."""
    insert_forecasts(sample_df, db_path=test_db)
    # Attempt injection through get_forecast
    malicious_input = "北部地區'; DROP TABLE TemperatureForecasts; --"
    df = get_forecast(malicious_input, db_path=test_db)
    assert len(df) == 0
    # Table should still exist
    regions = get_regions(db_path=test_db)
    assert len(regions) == 3


def test_clear_forecasts(test_db, sample_df):
    """Verify clear_forecasts removes all records."""
    insert_forecasts(sample_df, db_path=test_db)
    assert len(get_regions(db_path=test_db)) > 0
    clear_forecasts(db_path=test_db)
    assert len(get_regions(db_path=test_db)) == 0


def test_insert_empty_dataframe(test_db):
    """Verify inserting an empty DataFrame is safe and returns 0."""
    count = insert_forecasts(pd.DataFrame(), db_path=test_db)
    assert count == 0
