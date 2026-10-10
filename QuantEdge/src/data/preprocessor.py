"""Data preprocessing and chronological research splitting module.

Conforms to SOP-QUANT-001 (Section 11: Research Validation).
Enforces strict chronological train/validation/out-of-sample (OOS) splits
and walk-forward evaluation windows to prevent data leakage and overfitting.
"""

from typing import Tuple, List, Dict, Any
import pandas as pd


def split_train_val_test(
    df: pd.DataFrame,
    train_split: float = 0.60,
    val_split: float = 0.20,
    oos_split: float = 0.20
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Splits time series chronologically into Train, Validation, and Out-Of-Sample test sets.
    
    Parameters:
        df: Input DataFrame with DatetimeIndex (must be sorted chronologically).
        train_split: Fraction for training/in-sample period (e.g. 0.60).
        val_split: Fraction for validation/hyperparameter tuning (e.g. 0.20).
        oos_split: Fraction for untouched out-of-sample testing (e.g. 0.20).
        
    Returns:
        (train_df, val_df, oos_df)
        
    Raises:
        ValueError if splits do not sum to 1.0 or if dataset has insufficient rows.
    """
    total = train_split + val_split + oos_split
    if not (0.999 <= total <= 1.001):
        raise ValueError(f"Splits must sum to 1.0, got {total:.4f}")
        
    n = len(df)
    if n < 10:
        raise ValueError(f"Insufficient data points ({n}) for train/val/oos splitting.")
        
    # Strictly preserve chronological ordering
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()
        
    train_end = int(n * train_split)
    val_end = int(n * (train_split + val_split))
    
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    oos_df = df.iloc[val_end:].copy()
    
    return train_df, val_df, oos_df


def generate_walk_forward_windows(
    df: pd.DataFrame,
    is_bars: int = 250,
    oos_bars: int = 60,
    step_bars: int = 60
) -> List[Dict[str, Any]]:
    """Generates rolling Walk-Forward Optimization (WFO) windows over the historical dataset.
    
    Parameters:
        df: Input market data DataFrame with DatetimeIndex.
        is_bars: Number of bars for In-Sample training window.
        oos_bars: Number of bars for Out-of-Sample evaluation window.
        step_bars: Number of bars to slide forward for each window iteration.
        
    Returns:
        List of dicts containing window metadata, in_sample DataFrame, and out_of_sample DataFrame.
    """
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()
        
    n = len(df)
    windows = []
    start = 0
    window_idx = 1
    
    while start + is_bars + oos_bars <= n:
        is_end = start + is_bars
        oos_end = is_end + oos_bars
        
        is_data = df.iloc[start:is_end].copy()
        oos_data = df.iloc[is_end:oos_end].copy()
        
        windows.append({
            "window_id": window_idx,
            "is_start": is_data.index.min(),
            "is_end": is_data.index.max(),
            "oos_start": oos_data.index.min(),
            "oos_end": oos_data.index.max(),
            "in_sample": is_data,
            "out_of_sample": oos_data
        })
        
        start += step_bars
        window_idx += 1
        
    return windows
