"""Unit tests for SMA Crossover and RSI quantitative strategies."""

import pytest
import pandas as pd
import numpy as np

from src.strategies.sma_crossover import SMACrossoverStrategy
from src.strategies.rsi_strategy import RSIStrategy, calculate_wilder_rsi
from src.strategies.registry import get_strategy, list_strategies
from src.data.synthetic import (
    generate_synthetic_ohlcv,
    generate_step_trending_dataset,
    generate_oscillating_dataset
)


def test_sma_parameter_validation():
    """SMA strategy must validate parameters properly."""
    # fast >= slow must fail
    with pytest.raises(ValueError, match="strictly less than slow_period"):
        SMACrossoverStrategy({"fast_period": 50, "slow_period": 20})

    # negative window must fail
    with pytest.raises(ValueError, match="positive integer"):
        SMACrossoverStrategy({"fast_period": -5, "slow_period": 20})

    # invalid direction must fail
    with pytest.raises(ValueError, match="Invalid trade_direction"):
        SMACrossoverStrategy({"trade_direction": "invalid_mode"})


def test_sma_signal_generation_on_trend():
    """In a strictly ascending trend, fast SMA > slow SMA should produce long signals (1)."""
    trend_df = generate_step_trending_dataset(n_bars=60, initial_price=100.0, step=2.0)
    strat = SMACrossoverStrategy({"fast_period": 5, "slow_period": 15, "trade_direction": "long_only"})
    
    prepared = strat.run_signal_generation(trend_df)
    assert "sma_fast" in prepared.columns
    assert "sma_slow" in prepared.columns
    assert "signal" in prepared.columns
    
    # Warmup period before bar 15 must be 0
    assert (prepared["signal"].iloc[:14] == 0).all()
    # After bar 15 in strict uptrend, fast SMA > slow SMA -> signal must be 1
    assert (prepared["signal"].iloc[15:] == 1).all()


def test_rsi_parameter_validation():
    """RSI strategy must reject invalid thresholds."""
    with pytest.raises(ValueError, match="between 0.0 and 100.0"):
        RSIStrategy({"oversold_threshold": -5.0})

    with pytest.raises(ValueError, match="between 0.0 and 100.0"):
        RSIStrategy({"overbought_threshold": 120.0})

    with pytest.raises(ValueError, match="strictly less than overbought_threshold"):
        RSIStrategy({"oversold_threshold": 45.0, "overbought_threshold": 45.0})


def test_rsi_bounds_and_oscillating_signals():
    """RSI values must be strictly between 0 and 100, and generate trades on oscillating cycles."""
    cycle_df = generate_oscillating_dataset(n_bars=120, center_price=100.0, amplitude=20.0, period=25)
    strat = RSIStrategy({"rsi_period": 14, "oversold_threshold": 35.0, "overbought_threshold": 65.0})
    
    prepared = strat.run_signal_generation(cycle_df)
    rsi_vals = prepared["rsi"].dropna()
    assert (rsi_vals >= 0.0).all()
    assert (rsi_vals <= 100.0).all()
    
    # Signal must contain both in-position (1) and cash (0) regimes over oscillations
    signals = prepared["signal"]
    assert 1 in signals.values
    assert 0 in signals.values


def test_strategy_registry_discovery():
    """Strategy registry must list both strategies and allow retrieval."""
    registry = list_strategies()
    assert "sma_crossover" in registry
    assert "rsi_strategy" in registry
    
    s = get_strategy("sma_crossover", {"fast_period": 10, "slow_period": 30})
    assert s.params["fast_period"] == 10
