"""Deterministic synthetic market data generator conforming to SOP-QUANT-001.

Provides realistic synthetic OHLCV data for NSE stocks (e.g. TCS.NS) and benchmark indices (e.g. NIFTY 50),
as well as controlled synthetic datasets with known mathematical properties for unit testing.
"""

from pathlib import Path
from typing import Optional, Union
import numpy as np
import pandas as pd


def generate_synthetic_ohlcv(
    symbol: str = "TCS.NS",
    start_date: str = "2020-01-01",
    end_date: str = "2025-12-31",
    initial_price: float = 2200.0,
    annual_drift: float = 0.12,
    annual_volatility: float = 0.22,
    seed: int = 42,
    timeframe: str = "1d"
) -> pd.DataFrame:
    """Generates realistic daily OHLCV market data using Geometric Brownian Motion.
    
    Excludes weekends (Saturday & Sunday) to simulate standard NSE market sessions.
    
    Parameters:
        symbol: Instrument symbol identifier (e.g., 'TCS.NS', 'NIFTY50').
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        initial_price: Starting price in INR.
        annual_drift: Expected annualized return drift.
        annual_volatility: Expected annualized volatility (sigma).
        seed: Random seed for 100% deterministic reproducibility.
        timeframe: Bar timeframe (default '1d').
        
    Returns:
        pd.DataFrame with DatetimeIndex and ['open', 'high', 'low', 'close', 'volume', 'symbol'].
    """
    rng = np.random.default_rng(seed)
    
    # Generate business days only
    date_range = pd.bdate_range(start=start_date, end=end_date, freq="B")
    n_bars = len(date_range)
    if n_bars == 0:
        raise ValueError(f"No business days found between {start_date} and {end_date}")
        
    # Trading days per year
    dt = 1.0 / 252.0
    mu = annual_drift
    sigma = annual_volatility
    
    # GBM log returns for close prices
    daily_shocks = rng.normal(
        loc=(mu - 0.5 * sigma**2) * dt,
        scale=sigma * np.sqrt(dt),
        size=n_bars
    )
    
    # Cumulative price path
    log_prices = np.log(initial_price) + np.cumsum(daily_shocks)
    close_prices = np.exp(log_prices)
    
    # Generate realistic Open, High, Low relative to Close
    # Open is close of previous day plus overnight jump
    opens = np.empty(n_bars)
    opens[0] = initial_price
    overnight_gap_sd = 0.003
    for i in range(1, n_bars):
        gap = rng.normal(0, overnight_gap_sd)
        opens[i] = close_prices[i - 1] * (1.0 + gap)
        
    # High and Low are guaranteed to bound max(Open, Close) and min(Open, Close)
    # Intraday range fraction (e.g. 0.5% to 2.5%)
    highs = np.empty(n_bars)
    lows = np.empty(n_bars)
    
    for i in range(n_bars):
        max_oc = max(opens[i], close_prices[i])
        min_oc = min(opens[i], close_prices[i])
        
        # Upper shadow
        upper_wick = abs(rng.exponential(scale=0.006)) * max_oc
        highs[i] = round(max_oc + upper_wick, 2)
        
        # Lower shadow
        lower_wick = abs(rng.exponential(scale=0.006)) * min_oc
        lows[i] = round(max(0.01, min_oc - lower_wick), 2)
        
        opens[i] = round(opens[i], 2)
        close_prices[i] = round(close_prices[i], 2)
        
        # Verify strict invariants
        highs[i] = max(highs[i], opens[i], close_prices[i])
        lows[i] = min(lows[i], opens[i], close_prices[i])
        
    # Volume: Log-normal distribution with volume-volatility correlation
    base_volume = 1_500_000 if "TCS" in symbol.upper() else 10_000_000
    intraday_return = np.abs(close_prices - opens) / opens
    vol_multiplier = 1.0 + 5.0 * intraday_return
    volumes = np.round(
        base_volume * vol_multiplier * rng.lognormal(mean=0, sigma=0.4, size=n_bars)
    ).astype(int)
    
    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": close_prices,
            "volume": volumes,
            "symbol": symbol
        },
        index=date_range
    )
    df.index.name = "date"
    return df


def generate_flat_market_dataset(
    n_bars: int = 100,
    price: float = 1000.0,
    symbol: str = "FLAT.NS"
) -> pd.DataFrame:
    """Generates a perfectly flat market dataset (zero volatility) for edge-case testing."""
    dates = pd.bdate_range(start="2024-01-01", periods=n_bars)
    df = pd.DataFrame(
        {
            "open": np.full(n_bars, price),
            "high": np.full(n_bars, price),
            "low": np.full(n_bars, price),
            "close": np.full(n_bars, price),
            "volume": np.full(n_bars, 100000, dtype=int),
            "symbol": symbol
        },
        index=dates
    )
    df.index.name = "date"
    return df


def generate_step_trending_dataset(
    n_bars: int = 120,
    initial_price: float = 100.0,
    step: float = 2.0,
    symbol: str = "TREND.NS"
) -> pd.DataFrame:
    """Generates a strictly monotonically increasing price series for deterministic SMA cross test."""
    dates = pd.bdate_range(start="2024-01-01", periods=n_bars)
    closes = initial_price + np.arange(n_bars) * step
    opens = closes - 0.5
    highs = closes + 0.5
    lows = opens - 0.5
    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.full(n_bars, 50000, dtype=int),
            "symbol": symbol
        },
        index=dates
    )
    df.index.name = "date"
    return df


def generate_oscillating_dataset(
    n_bars: int = 100,
    center_price: float = 100.0,
    amplitude: float = 15.0,
    period: int = 20,
    symbol: str = "CYCLE.NS"
) -> pd.DataFrame:
    """Generates a sinusoidal oscillating price series for deterministic RSI cycle testing."""
    dates = pd.bdate_range(start="2024-01-01", periods=n_bars)
    t = np.arange(n_bars)
    closes = center_price + amplitude * np.sin(2 * np.pi * t / period)
    opens = closes - 0.2
    highs = np.maximum(opens, closes) + 0.5
    lows = np.minimum(opens, closes) - 0.5
    df = pd.DataFrame(
        {
            "open": np.round(opens, 2),
            "high": np.round(highs, 2),
            "low": np.round(lows, 2),
            "close": np.round(closes, 2),
            "volume": np.full(n_bars, 50000, dtype=int),
            "symbol": symbol
        },
        index=dates
    )
    df.index.name = "date"
    return df


def save_default_sample_datasets(output_dir: Union[str, Path] = "data/sample") -> None:
    """Generates and writes default sample datasets (TCS.NS, NIFTY50) to the sample directory."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. TCS.NS sample daily (2020 to 2025)
    tcs_df = generate_synthetic_ohlcv(
        symbol="TCS.NS",
        start_date="2020-01-01",
        end_date="2025-12-31",
        initial_price=2160.0,
        annual_drift=0.14,
        annual_volatility=0.21,
        seed=101
    )
    tcs_path = out_dir / "tcs_sample_daily.csv"
    tcs_df.to_csv(tcs_path)
    
    # 2. NIFTY 50 Benchmark index sample daily (2020 to 2025)
    nifty_df = generate_synthetic_ohlcv(
        symbol="NIFTY_50",
        start_date="2020-01-01",
        end_date="2025-12-31",
        initial_price=12180.0,
        annual_drift=0.12,
        annual_volatility=0.16,
        seed=202
    )
    nifty_path = out_dir / "nifty50_sample_daily.csv"
    nifty_df.to_csv(nifty_path)
