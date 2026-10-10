"""Unit tests for market data loading and validation conforming to SOP-QUANT-001."""

import pytest
import pandas as pd
import numpy as np

from src.data.validator import validate_market_data, DataValidationResult
from src.data.synthetic import generate_synthetic_ohlcv, generate_flat_market_dataset


def test_valid_market_data_passes():
    """Valid synthetic dataset must pass validation with is_valid=True."""
    df = generate_synthetic_ohlcv(symbol="TCS.NS", start_date="2024-01-01", end_date="2024-03-31", seed=42)
    res = validate_market_data(df, source_name="test_valid")
    assert res.is_valid is True
    assert len(res.errors) == 0
    assert res.clean_data is not None
    assert len(res.clean_data) > 0
    assert "close" in res.clean_data.columns


def test_negative_or_zero_price_rejected():
    """Zero or negative prices must be caught and rejected."""
    df = generate_synthetic_ohlcv(start_date="2024-01-01", end_date="2024-02-01", seed=1)
    # Inject non-positive price
    df.iloc[5, df.columns.get_loc("close")] = -10.0
    res = validate_market_data(df)
    assert res.is_valid is False
    assert any("zero or negative" in err.lower() for err in res.errors)

    df.iloc[5, df.columns.get_loc("close")] = 0.0
    res2 = validate_market_data(df)
    assert res2.is_valid is False


def test_invalid_ohlc_relationships_rejected():
    """High < Low, High < Open, or Low > Close must trigger validation errors."""
    # Test High < Low
    df1 = generate_synthetic_ohlcv(start_date="2024-01-01", end_date="2024-02-01", seed=2)
    df1.iloc[3, df1.columns.get_loc("high")] = df1.iloc[3, df1.columns.get_loc("low")] - 5.0
    res1 = validate_market_data(df1)
    assert res1.is_valid is False
    assert any("high < low" in err.lower() for err in res1.errors)

    # Test High < Close
    df2 = generate_synthetic_ohlcv(start_date="2024-01-01", end_date="2024-02-01", seed=3)
    df2.iloc[4, df2.columns.get_loc("high")] = df2.iloc[4, df2.columns.get_loc("close")] - 2.0
    res2 = validate_market_data(df2)
    assert res2.is_valid is False
    assert any("high is less than" in err.lower() for err in res2.errors)


def test_duplicate_and_unsorted_timestamps_handled():
    """Unsorted and duplicate timestamps must be audited, sorted, and deduplicated."""
    df = generate_synthetic_ohlcv(start_date="2024-01-01", end_date="2024-02-01", seed=4)
    # Shuffle order
    shuffled_df = df.sample(frac=1.0, random_state=42)
    # Append duplicate row
    dup_row = df.iloc[[0]].copy()
    mixed_df = pd.concat([shuffled_df, dup_row])

    res = validate_market_data(mixed_df)
    assert res.is_valid is True
    assert any("duplicate" in w.lower() for w in res.warnings)
    assert any("sorted" in w.lower() for w in res.warnings)
    assert res.clean_data.index.is_monotonic_increasing


def test_empty_dataset_rejected():
    """Empty DataFrame must fail gracefully."""
    empty_df = pd.DataFrame()
    res = validate_market_data(empty_df)
    assert res.is_valid is False
    assert len(res.errors) > 0


def test_nan_handling_without_silent_fabrication():
    """NaNs in price/volume must be dropped with transparent warning, never silently fabricated."""
    df = generate_synthetic_ohlcv(start_date="2024-01-01", end_date="2024-02-01", seed=5)
    raw_len = len(df)
    df.iloc[2, df.columns.get_loc("open")] = np.nan
    res = validate_market_data(df)
    assert res.is_valid is True
    assert any("nan" in w.lower() for w in res.warnings)
    assert len(res.clean_data) == raw_len - 1
