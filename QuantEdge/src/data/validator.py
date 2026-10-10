"""Data validation module conforming to SOP-QUANT-001 (Section 5: Historical Data Ingestion).

Guarantees data integrity, chronologically sorts records, detects duplicates,
validates strict OHLC relationships, checks for non-positive prices, and generates
transparent data quality metrics and warnings. Never silently fabricates missing prices.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


@dataclass
class DataValidationResult:
    """Holds the outcome of market data validation."""
    is_valid: bool
    clean_data: Optional[pd.DataFrame] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    raw_record_count: int = 0
    clean_record_count: int = 0


def validate_market_data(
    df: pd.DataFrame,
    source_name: str = "custom_upload",
    allow_zero_volume: bool = True,
    strict_ohlc: bool = True
) -> DataValidationResult:
    """Validates raw market data DataFrame against quantitative finance standards.
    
    Parameters:
        df: Input DataFrame containing market data.
        source_name: Name or file path of the data source for auditing.
        allow_zero_volume: Whether 0 volume is flagged as a warning instead of error.
        strict_ohlc: Enforce High >= max(Open, Close) and Low <= min(Open, Close).
        
    Returns:
        DataValidationResult with validation status, clean DataFrame, errors, and warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []
    metrics: Dict[str, Any] = {"source": source_name}
    
    if df is None or df.empty:
        return DataValidationResult(
            is_valid=False,
            errors=["Dataset is empty or None."],
            metrics=metrics,
            raw_record_count=0,
            clean_record_count=0
        )
    
    raw_count = len(df)
    metrics["raw_rows"] = raw_count
    
    # 1. Standardize column names (case-insensitive, strip whitespace)
    working_df = df.copy()
    col_map = {str(c).strip().lower(): c for c in working_df.columns}
    
    # Required core columns
    required_cols = ["open", "high", "low", "close", "volume"]
    missing_cols = [rc for rc in required_cols if rc not in col_map]
    
    # Check for date / timestamp column
    date_candidates = ["timestamp", "date", "datetime", "time"]
    found_date_col = None
    for cand in date_candidates:
        if cand in col_map:
            found_date_col = col_map[cand]
            break
            
    if found_date_col is None and not isinstance(working_df.index, pd.DatetimeIndex):
        errors.append(f"Missing required date/timestamp column. Looked for one of {date_candidates} or DatetimeIndex.")
        
    if missing_cols:
        errors.append(f"Missing required price/volume columns: {missing_cols}. Found: {list(df.columns)}")
        
    if errors:
        return DataValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
            raw_record_count=raw_count,
            clean_record_count=0
        )
        
    # Standardize column renaming
    rename_dict = {col_map[rc]: rc for rc in required_cols}
    if found_date_col:
        rename_dict[found_date_col] = "date"
    working_df = working_df.rename(columns=rename_dict)
    
    # 2. Date parsing and sorting
    if "date" in working_df.columns:
        try:
            working_df["date"] = pd.to_datetime(working_df["date"])
        except Exception as e:
            errors.append(f"Failed to parse dates into datetime objects: {e}")
            return DataValidationResult(is_valid=False, errors=errors, warnings=warnings, metrics=metrics)
        working_df = working_df.set_index("date")
    elif isinstance(working_df.index, pd.DatetimeIndex):
        working_df.index.name = "date"
    else:
        errors.append("Invalid date representation.")
        return DataValidationResult(is_valid=False, errors=errors, warnings=warnings, metrics=metrics)
        
    # Remove timezone offset or localize to tz-naive UTC for consistent math
    if working_df.index.tz is not None:
        warnings.append(f"Timezone detected ({working_df.index.tz}). Normalizing index to timezone-naive UTC.")
        working_df.index = working_df.index.tz_convert("UTC").tz_localize(None)
        
    # 3. Detect duplicate timestamps
    dup_mask = working_df.index.duplicated(keep="last")
    dup_count = int(dup_mask.sum())
    if dup_count > 0:
        warnings.append(f"Detected {dup_count} duplicate timestamps. Deduplicating by keeping the latest record.")
        working_df = working_df[~dup_mask]
        
    # Chronological sort
    if not working_df.index.is_monotonic_increasing:
        warnings.append("Dataset was not in chronological order. Sorted records chronologically.")
        working_df = working_df.sort_index()
        
    # 4. Data types and numeric conversions
    for col in required_cols:
        try:
            working_df[col] = pd.to_numeric(working_df[col], errors="coerce")
        except Exception as e:
            errors.append(f"Failed to convert column '{col}' to numeric: {e}")
            
    if errors:
        return DataValidationResult(is_valid=False, errors=errors, warnings=warnings, metrics=metrics)
        
    # 5. Missing values check (NaN / Null)
    nan_counts = working_df[required_cols].isna().sum()
    total_nans = int(nan_counts.sum())
    if total_nans > 0:
        nan_summary = {k: int(v) for k, v in nan_counts.items() if v > 0}
        warnings.append(f"Found {total_nans} NaN values across columns: {nan_summary}. Dropping invalid rows (never silently fabricating prices).")
        working_df = working_df.dropna(subset=required_cols)
        
    if working_df.empty:
        errors.append("All rows were dropped due to NaN values.")
        return DataValidationResult(is_valid=False, errors=errors, warnings=warnings, metrics=metrics)
        
    # 6. Non-positive price check (Price <= 0 is strictly invalid in cash equity)
    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        non_pos = working_df[col] <= 0
        non_pos_count = int(non_pos.sum())
        if non_pos_count > 0:
            errors.append(f"Column '{col}' has {non_pos_count} zero or negative price entries (min: {working_df[col].min()}). Non-positive prices are invalid.")
            
    # Volume non-negativity
    neg_vol_count = int((working_df["volume"] < 0).sum())
    if neg_vol_count > 0:
        errors.append(f"Volume has {neg_vol_count} negative entries. Volume cannot be negative.")
        
    zero_vol_count = int((working_df["volume"] == 0).sum())
    if zero_vol_count > 0:
        if allow_zero_volume:
            warnings.append(f"Volume has {zero_vol_count} zero-volume bars (potential illiquid periods or non-trading sessions).")
        else:
            errors.append(f"Volume has {zero_vol_count} zero-volume bars.")
            
    if errors:
        return DataValidationResult(is_valid=False, errors=errors, warnings=warnings, metrics=metrics)
        
    # 7. Strict OHLC geometric sanity check:
    # High >= max(Open, Close) and Low <= min(Open, Close)
    # High >= Low
    invalid_hl = working_df["high"] < working_df["low"]
    hl_count = int(invalid_hl.sum())
    if hl_count > 0:
        errors.append(f"Detected {hl_count} bars where High < Low.")
        
    if strict_ohlc:
        invalid_high = (working_df["high"] < working_df["open"]) | (working_df["high"] < working_df["close"])
        high_err_count = int(invalid_high.sum())
        if high_err_count > 0:
            errors.append(f"Detected {high_err_count} bars where High is less than Open or Close.")
            
        invalid_low = (working_df["low"] > working_df["open"]) | (working_df["low"] > working_df["close"])
        low_err_count = int(invalid_low.sum())
        if low_err_count > 0:
            errors.append(f"Detected {low_err_count} bars where Low is greater than Open or Close.")
            
    if errors:
        return DataValidationResult(is_valid=False, errors=errors, warnings=warnings, metrics=metrics)
        
    # 8. Date range and session statistics
    clean_count = len(working_df)
    start_date = working_df.index.min()
    end_date = working_df.index.max()
    
    metrics.update({
        "clean_rows": clean_count,
        "dropped_rows": raw_count - clean_count,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "total_days_span": (end_date - start_date).days if start_date and end_date else 0,
        "min_close": float(working_df["close"].min()),
        "max_close": float(working_df["close"].max()),
        "avg_daily_volume": float(working_df["volume"].mean()),
        "zero_volume_bars": zero_vol_count,
        "duplicate_timestamps": dup_count
    })
    
    return DataValidationResult(
        is_valid=True,
        clean_data=working_df,
        errors=[],
        warnings=warnings,
        metrics=metrics,
        raw_record_count=raw_count,
        clean_record_count=clean_count
    )
