"""
validate_weather.py - Validation layer for CWA Weather Data.

Ensures that only clean, well-formed, and physically plausible weather records
reach the database and presentation layers.
"""

import re
import datetime
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["regionName", "dataDate", "minT", "maxT"]

# Temperature physical bounds for Taiwan (°C)
MIN_TEMPERATURE_BOUND = -15.0  # High mountain winter low rarely drops below -12°C
MAX_TEMPERATURE_BOUND = 45.0   # Highest recorded temperature in Taiwan history is ~40.2°C


class WeatherValidationError(Exception):
    """Raised when weather data fails strict validation checks."""
    pass


@dataclass
class ValidationResult:
    """Summary of data validation execution."""
    is_valid: bool
    validated_df: pd.DataFrame
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_rows: int = 0
    valid_rows: int = 0
    dropped_rows: int = 0


def is_valid_calendar_date(date_str: Any) -> bool:
    """Checks if date_str is a valid YYYY-MM-DD calendar date."""
    if not isinstance(date_str, str):
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_weather_dataframe(
    df: pd.DataFrame,
    strict: bool = False
) -> ValidationResult:
    """
    Validates a weather DataFrame against project rules.

    Validation Rules:
      1. Required columns exist: regionName, dataDate, minT, maxT.
      2. regionName must be non-empty and non-null.
      3. dataDate must be a valid YYYY-MM-DD calendar date.
      4. minT and maxT must be numeric (not NaN/null).
      5. minT <= maxT (no temperature inversion).
      6. minT and maxT must be within plausible physical bounds (-15°C to 45°C).
      7. Duplicate records (same regionName and dataDate) are detected.

    Args:
        df: Input DataFrame to validate.
        strict: If True, raises WeatherValidationError on first error.

    Returns:
        ValidationResult with validated_df containing only valid rows.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Check schema
    if not isinstance(df, pd.DataFrame):
        err = f"Expected pandas DataFrame, got {type(df).__name__}."
        if strict:
            raise WeatherValidationError(err)
        return ValidationResult(
            is_valid=False,
            validated_df=pd.DataFrame(columns=REQUIRED_COLUMNS),
            errors=[err]
        )

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        err = f"Missing required columns: {', '.join(missing_cols)}."
        if strict:
            raise WeatherValidationError(err)
        return ValidationResult(
            is_valid=False,
            validated_df=pd.DataFrame(columns=REQUIRED_COLUMNS),
            errors=[err]
        )

    total_rows = len(df)
    if total_rows == 0:
        return ValidationResult(
            is_valid=True,
            validated_df=df.copy(),
            errors=[],
            warnings=[],
            total_rows=0,
            valid_rows=0,
            dropped_rows=0
        )

    valid_indices = []

    # 2. Check for duplicate region + date pairs
    dup_mask = df.duplicated(subset=["regionName", "dataDate"], keep=False)
    if dup_mask.any():
        dups = df[dup_mask][["regionName", "dataDate"]].drop_duplicates()
        for _, dup_row in dups.iterrows():
            err_msg = (
                f"Duplicate record detected for region '{dup_row['regionName']}' "
                f"on date '{dup_row['dataDate']}'."
            )
            errors.append(err_msg)

    # 3. Validate each row
    seen_keys: Set[Tuple[str, str]] = set()

    for idx, row in df.iterrows():
        row_errors = []
        region = row.get("regionName")
        date_val = row.get("dataDate")
        min_t = row.get("minT")
        max_t = row.get("maxT")

        # Validate regionName
        if pd.isna(region) or not str(region).strip():
            row_errors.append(f"Row {idx}: regionName is missing or empty.")

        # Validate dataDate
        if pd.isna(date_val) or not is_valid_calendar_date(str(date_val)):
            row_errors.append(f"Row {idx}: dataDate '{date_val}' is invalid or not in YYYY-MM-DD format.")

        # Validate numeric minT
        if pd.isna(min_t):
            row_errors.append(f"Row {idx}: minT is missing or null.")
            min_t = None
        else:
            try:
                min_t = float(min_t)
                if pd.isna(min_t):
                    row_errors.append(f"Row {idx}: minT is missing or null.")
                    min_t = None
            except (ValueError, TypeError):
                row_errors.append(f"Row {idx}: minT '{min_t}' is not a valid number.")
                min_t = None

        # Validate numeric maxT
        if pd.isna(max_t):
            row_errors.append(f"Row {idx}: maxT is missing or null.")
            max_t = None
        else:
            try:
                max_t = float(max_t)
                if pd.isna(max_t):
                    row_errors.append(f"Row {idx}: maxT is missing or null.")
                    max_t = None
            except (ValueError, TypeError):
                row_errors.append(f"Row {idx}: maxT '{max_t}' is not a valid number.")
                max_t = None

        # Check physical plausibility and temperature inversion
        if min_t is not None and max_t is not None:
            if min_t > max_t:
                row_errors.append(
                    f"Row {idx}: minT ({min_t}) cannot be greater than maxT ({max_t}) "
                    f"for region '{region}' on {date_val}."
                )

            if min_t < MIN_TEMPERATURE_BOUND or min_t > MAX_TEMPERATURE_BOUND:
                row_errors.append(
                    f"Row {idx}: minT ({min_t}°C) exceeds realistic bounds "
                    f"[{MIN_TEMPERATURE_BOUND}°C, {MAX_TEMPERATURE_BOUND}°C]."
                )

            if max_t < MIN_TEMPERATURE_BOUND or max_t > MAX_TEMPERATURE_BOUND:
                row_errors.append(
                    f"Row {idx}: maxT ({max_t}°C) exceeds realistic bounds "
                    f"[{MIN_TEMPERATURE_BOUND}°C, {MAX_TEMPERATURE_BOUND}°C]."
                )

        # Check deduplication for validated_df
        pair_key = (str(region).strip(), str(date_val).strip())
        if pair_key in seen_keys:
            # We already reported duplicate in step 2; drop subsequent instances
            row_errors.append(f"Row {idx}: Duplicate entry for {pair_key} dropped.")
        elif not row_errors:
            seen_keys.add(pair_key)

        if row_errors:
            errors.extend(row_errors)
        else:
            valid_indices.append(idx)

    if strict and errors:
        raise WeatherValidationError(f"Validation failed with {len(errors)} error(s):\n" + "\n".join(errors[:5]))

    validated_df = df.loc[valid_indices].copy().reset_index(drop=True)
    valid_rows = len(validated_df)
    dropped_rows = total_rows - valid_rows

    if dropped_rows > 0:
        warnings.append(f"{dropped_rows} row(s) were dropped due to validation errors.")

    return ValidationResult(
        is_valid=(len(errors) == 0),
        validated_df=validated_df,
        errors=errors,
        warnings=warnings,
        total_rows=total_rows,
        valid_rows=valid_rows,
        dropped_rows=dropped_rows
    )
