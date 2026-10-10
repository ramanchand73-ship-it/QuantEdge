"""QuantEdge - Exploratory Quantitative Research Script.

Allows rapid strategy prototyping, parameter sensitivity testing,
and comparison between SMA Crossover and RSI strategies.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.data.loader import load_market_data
from src.strategies.sma_crossover import SMACrossoverStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.backtesting.engine import BacktestEngine
from src.backtesting.costs import load_cost_model
from src.risk.metrics import calculate_performance_metrics


def run_exploration():
    print("=== QuantEdge Research Prototyping ===")
    data_path = Path("data/sample/tcs_sample_daily.csv")
    benchmark_path = Path("data/sample/nifty50_sample_daily.csv")
    
    df = load_market_data(data_path)
    b_df = load_market_data(benchmark_path)
    
    cost_model = load_cost_model("nse_equity_delivery")
    
    # 1. Test SMA Crossover
    sma_strat = SMACrossoverStrategy({"fast_period": 15, "slow_period": 45})
    engine_sma = BacktestEngine(strategy=sma_strat, cost_model=cost_model, initial_capital=1_000_000.0)
    res_sma = engine_sma.run(df, benchmark_data=b_df)
    metrics_sma = calculate_performance_metrics(res_sma.equity_curve, res_sma.trades, res_sma.initial_capital, res_sma.benchmark_equity)
    
    # 2. Test RSI Strategy
    rsi_strat = RSIStrategy({"rsi_period": 14, "oversold_threshold": 30.0, "overbought_threshold": 70.0})
    engine_rsi = BacktestEngine(strategy=rsi_strat, cost_model=cost_model, initial_capital=1_000_000.0)
    res_rsi = engine_rsi.run(df, benchmark_data=b_df)
    metrics_rsi = calculate_performance_metrics(res_rsi.equity_curve, res_rsi.trades, res_rsi.initial_capital, res_rsi.benchmark_equity)
    
    print("\n--- Strategy Comparison ---")
    print(f"SMA Crossover | CAGR: {metrics_sma['cagr_pct']:.2f}% | Sharpe: {metrics_sma['sharpe_ratio']:.2f} | MaxDD: {metrics_sma['max_drawdown_pct']:.2f}% | Trades: {metrics_sma['total_closed_trades']}")
    print(f"RSI Strategy  | CAGR: {metrics_rsi['cagr_pct']:.2f}% | Sharpe: {metrics_rsi['sharpe_ratio']:.2f} | MaxDD: {metrics_rsi['max_drawdown_pct']:.2f}% | Trades: {metrics_rsi['total_closed_trades']}")
    print(f"Benchmark     | Net Return: {metrics_sma['benchmark_return_pct']:.2f}%")


if __name__ == "__main__":
    run_exploration()
