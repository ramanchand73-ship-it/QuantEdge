"""Unit tests for simulation determinism and reproducibility conforming to SOP-QUANT-001."""

import pytest
import pandas as pd
import numpy as np

from src.strategies.sma_crossover import SMACrossoverStrategy
from src.backtesting.engine import BacktestEngine
from src.backtesting.costs import load_cost_model
from src.data.synthetic import generate_synthetic_ohlcv


def test_simulation_reproducibility():
    """Running identical backtests sequentially must produce bit-for-bit identical outputs."""
    df = generate_synthetic_ohlcv(symbol="TCS.NS", start_date="2023-01-01", end_date="2024-06-30", seed=99)
    strat = SMACrossoverStrategy({"fast_period": 10, "slow_period": 30})
    cost_model = load_cost_model("nse_equity_delivery")
    
    engine1 = BacktestEngine(strategy=strat, cost_model=cost_model, initial_capital=1_000_000.0, signal_delay_bars=1)
    res1 = engine1.run(df)
    
    engine2 = BacktestEngine(strategy=strat, cost_model=cost_model, initial_capital=1_000_000.0, signal_delay_bars=1)
    res2 = engine2.run(df)
    
    # Assert final equity matches exactly
    assert res1.final_equity == res2.final_equity
    assert res1.total_net_pnl == res2.total_net_pnl
    
    # Assert equity curves match exactly
    pd.testing.assert_frame_equal(res1.equity_curve, res2.equity_curve)
    
    # Assert trades match exactly
    pd.testing.assert_frame_equal(res1.trades, res2.trades)
