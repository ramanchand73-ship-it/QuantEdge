"""Verification suite for Look-Ahead Bias and Order Timing Causality.

Conforms to SOP-QUANT-001 (Section 6, 7, & 13: Look-Ahead Bias & Execution Timing).
1. Verifies that future data mutations do not alter past indicator values or signals.
2. Verifies that orders generated at Bar T Close strictly execute at Bar T+1 Open.
"""

import pytest
import pandas as pd
import numpy as np

from src.strategies.sma_crossover import SMACrossoverStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.backtesting.engine import BacktestEngine
from src.backtesting.costs import CostModel
from src.data.synthetic import generate_synthetic_ohlcv


def test_sma_no_lookahead_on_future_mutation():
    """Mutating future price bars must NOT affect past SMA indicators or signals at bar T."""
    df = generate_synthetic_ohlcv(symbol="TCS.NS", start_date="2024-01-01", end_date="2024-06-30", seed=42)
    strat = SMACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    
    # Baseline run
    baseline = strat.run_signal_generation(df)
    
    # Pick a historical decision point T
    T = 50
    baseline_fast_t = baseline["sma_fast"].iloc[T]
    baseline_slow_t = baseline["sma_slow"].iloc[T]
    baseline_signal_t = baseline["signal"].iloc[T]
    
    # Mutate future bars (from T+1 onward) with drastic price changes
    mutated_df = df.copy()
    mutated_df.iloc[T + 1:, mutated_df.columns.get_loc("close")] *= 5.0
    mutated_df.iloc[T + 1:, mutated_df.columns.get_loc("high")] *= 5.0
    mutated_df.iloc[T + 1:, mutated_df.columns.get_loc("low")] *= 5.0
    
    # Re-run strategy on mutated data
    mutated_res = strat.run_signal_generation(mutated_df)
    
    # Assert past values are mathematically identical
    assert np.isclose(mutated_res["sma_fast"].iloc[T], baseline_fast_t)
    assert np.isclose(mutated_res["sma_slow"].iloc[T], baseline_slow_t)
    assert mutated_res["signal"].iloc[T] == baseline_signal_t
    
    # Assert entire history up to T is identical
    pd.testing.assert_series_equal(mutated_res["signal"].iloc[:T+1], baseline["signal"].iloc[:T+1])


def test_rsi_no_lookahead_on_future_mutation():
    """Mutating future price bars must NOT affect past RSI indicator or signals at bar T."""
    df = generate_synthetic_ohlcv(symbol="TCS.NS", start_date="2024-01-01", end_date="2024-06-30", seed=42)
    strat = RSIStrategy({"rsi_period": 14, "oversold_threshold": 30.0, "overbought_threshold": 70.0})
    
    baseline = strat.run_signal_generation(df)
    T = 45
    
    baseline_rsi_t = baseline["rsi"].iloc[T]
    baseline_signal_t = baseline["signal"].iloc[T]
    
    # Mutate future data
    mutated_df = df.copy()
    mutated_df.iloc[T + 1:, mutated_df.columns.get_loc("close")] *= 0.2
    
    mutated_res = strat.run_signal_generation(mutated_df)
    
    assert np.isclose(mutated_res["rsi"].iloc[T], baseline_rsi_t)
    assert mutated_res["signal"].iloc[T] == baseline_signal_t
    pd.testing.assert_series_equal(mutated_res["signal"].iloc[:T+1], baseline["signal"].iloc[:T+1])


def test_order_timing_executes_at_t_plus_1_open():
    """A signal emitted at Bar T Close MUST execute at Bar T+1 Open, NOT at Bar T Close."""
    # Build deterministic scenario
    df = generate_synthetic_ohlcv(symbol="TEST.NS", start_date="2024-01-01", end_date="2024-03-31", seed=77)
    strat = SMACrossoverStrategy({"fast_period": 5, "slow_period": 15})
    
    # Zero cost to isolate pure price fill
    zero_cost = CostModel(name="zero_cost", default_slippage_bps=0.0, default_half_spread_bps=0.0)
    
    engine = BacktestEngine(
        strategy=strat,
        cost_model=zero_cost,
        initial_capital=500_000.0,
        signal_delay_bars=1,
        close_positions_at_end=False
    )
    
    result = engine.run(df)
    trades = result.trades
    
    assert not trades.empty, "Test dataset should have produced at least one trade."
    first_trade = trades.iloc[0]
    entry_time = pd.to_datetime(first_trade["entry_time"])
    entry_px = first_trade["entry_price"]
    
    # Verify the fill price matches the OPEN price of entry_time
    expected_open_px = df.loc[entry_time, "open"]
    assert np.isclose(entry_px, expected_open_px), (
        f"Executed price {entry_px} does not match Bar T+1 Open {expected_open_px}"
    )
