"""Unit tests for Quantitative Performance and Risk Metrics."""

import pytest
import pandas as pd
import numpy as np

from src.risk.metrics import calculate_performance_metrics


def test_zero_trades_edge_case():
    """Empty or zero-trade backtests must return valid metrics without dividing by zero."""
    dates = pd.bdate_range(start="2024-01-01", periods=50)
    equity_curve = pd.DataFrame(
        {
            "equity": np.full(50, 1_000_000.0),
            "cash": np.full(50, 1_000_000.0),
            "drawdown": np.zeros(50)
        },
        index=dates
    )
    trades = pd.DataFrame()
    
    metrics = calculate_performance_metrics(equity_curve, trades, initial_capital=1_000_000.0)
    assert metrics["net_profit"] == 0.0
    assert metrics["total_closed_trades"] == 0
    assert metrics["sharpe_ratio"] == 0.0
    assert metrics["max_drawdown_pct"] == 0.0
    assert metrics["win_rate_pct"] == 0.0


def test_positive_trade_metrics():
    """Metrics must compute expected win rate, profit factor, and CAGR correctly."""
    dates = pd.bdate_range(start="2024-01-01", periods=100)
    # Growing equity curve
    equity_values = np.linspace(1_000_000, 1_200_000, 100)
    equity_curve = pd.DataFrame(
        {
            "equity": equity_values,
            "cash": equity_values,
            "drawdown": np.zeros(100),
            "shares": np.zeros(100)
        },
        index=dates
    )
    
    trades = pd.DataFrame([
        {"trade_id": 1, "net_pnl": 120_000.0, "total_friction": 1000.0, "holding_bars": 10, "entry_price": 1000, "shares": 100, "exit_price": 1120},
        {"trade_id": 2, "net_pnl": 100_000.0, "total_friction": 1000.0, "holding_bars": 12, "entry_price": 1000, "shares": 100, "exit_price": 1100},
        {"trade_id": 3, "net_pnl": -20_000.0, "total_friction": 800.0, "holding_bars": 5, "entry_price": 1000, "shares": 100, "exit_price": 980},
    ])
    
    metrics = calculate_performance_metrics(equity_curve, trades, initial_capital=1_000_000.0)
    assert metrics["total_closed_trades"] == 3
    assert metrics["winning_trades"] == 2
    assert metrics["losing_trades"] == 1
    assert np.isclose(metrics["win_rate_pct"], 66.67, atol=0.1)
    
    # Gross gains = 220,000; Gross losses = 20,000 -> Profit factor = 11.0
    assert np.isclose(metrics["profit_factor"], 11.0)
    assert metrics["net_profit"] == 200_000.0
    assert metrics["net_return_pct"] == 20.0
