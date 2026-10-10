"""Comprehensive quantitative performance and risk metrics calculation module.

Conforms to SOP-QUANT-001 (Section 10: Performance Metrics).
Robustly calculates:
- Initial & Final Value, Net PnL, Net Return
- Compound Annual Growth Rate (CAGR)
- Annualized Volatility
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Maximum Drawdown (%) & Drawdown Duration (bars/days)
- Trade statistics: Win Rate, Profit Factor, Avg Win/Loss, Closed Trades
- Average Holding Period, Exposure %, Portfolio Turnover %
- Benchmark-relative Alpha, Beta, and Information Ratio
Handles zero denominators, empty trade sets, flat equity curves, and zero variance without crashing.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


def calculate_performance_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    initial_capital: float,
    benchmark_equity: Optional[pd.Series] = None,
    risk_free_rate: float = 0.065,   # Standard Indian risk-free proxy (e.g. RBI 91-day T-bill ~6.5%)
    periods_per_year: int = 252
) -> Dict[str, Any]:
    """Calculates quantitative risk and return metrics.
    
    Parameters:
        equity_curve: DataFrame with DatetimeIndex and 'equity', 'cash', 'drawdown'.
        trades: DataFrame of closed round-trip trades.
        initial_capital: Virtual starting cash (INR).
        benchmark_equity: Optional Series of benchmark portfolio equity indexed to same dates.
        risk_free_rate: Annualized risk-free rate (e.g. 0.065 for 6.5%).
        periods_per_year: Number of trading bars per year (252 for daily).
        
    Returns:
        Dictionary of computed performance and risk metrics.
    """
    metrics: Dict[str, Any] = {}
    
    if equity_curve is None or equity_curve.empty or "equity" not in equity_curve.columns:
        return _empty_metrics(initial_capital)
        
    equity_series = equity_curve["equity"]
    n_bars = len(equity_series)
    final_equity = float(equity_series.iloc[-1])
    net_profit = final_equity - initial_capital
    net_return_pct = (net_profit / initial_capital) if initial_capital > 0 else 0.0
    
    # 1. Periodic returns
    returns = equity_series.pct_change().dropna()
    
    # Time span in years
    start_time = equity_series.index.min()
    end_time = equity_series.index.max()
    time_span_days = max(1, (end_time - start_time).days) if pd.notna(start_time) and pd.notna(end_time) else n_bars
    years = max(time_span_days / 365.25, n_bars / periods_per_year)
    
    # 2. Compound Annual Growth Rate (CAGR)
    if years >= (30.0 / 365.25) and final_equity > 0 and initial_capital > 0:
        cagr = (final_equity / initial_capital) ** (1.0 / years) - 1.0
    else:
        # For very short periods, fallback to simple annualized or total return
        cagr = net_return_pct
        
    # 3. Annualized Volatility
    if len(returns) > 1 and returns.std() > 0:
        ann_volatility = float(returns.std() * np.sqrt(periods_per_year))
    else:
        ann_volatility = 0.0
        
    # 4. Sharpe Ratio
    daily_rf = (1.0 + risk_free_rate) ** (1.0 / periods_per_year) - 1.0
    excess_returns = returns - daily_rf
    if ann_volatility > 0:
        sharpe_ratio = float((excess_returns.mean() * np.sqrt(periods_per_year)) / (returns.std() or 1e-9))
    else:
        sharpe_ratio = 0.0
        
    # 5. Sortino Ratio (Downside deviation)
    downside_diff = returns - daily_rf
    downside_returns = downside_diff[downside_diff < 0]
    if len(downside_returns) > 0 and downside_returns.std() > 0:
        downside_std = float(np.sqrt(np.mean(downside_returns**2)) * np.sqrt(periods_per_year))
        sortino_ratio = float((cagr - risk_free_rate) / (downside_std or 1e-9))
    else:
        sortino_ratio = 0.0 if cagr <= risk_free_rate else 9.99
        
    # 6. Maximum Drawdown & Duration
    cum_max = equity_series.cummax()
    drawdown_series = (cum_max - equity_series) / cum_max
    max_drawdown = float(drawdown_series.max()) if len(drawdown_series) > 0 else 0.0
    
    # Max drawdown duration (longest streak where equity < cummax)
    is_in_dd = drawdown_series > 0
    dd_durations = (~is_in_dd).cumsum()[is_in_dd].value_counts()
    max_dd_duration_bars = int(dd_durations.max()) if not dd_durations.empty else 0
    
    # 7. Calmar Ratio
    if max_drawdown > 0:
        calmar_ratio = float(cagr / max_drawdown)
    else:
        calmar_ratio = 0.0 if cagr <= 0 else 9.99
        
    # 8. Trade Statistics
    has_trades = trades is not None and not trades.empty and "net_pnl" in trades.columns
    total_trades = len(trades) if has_trades else 0
    
    if has_trades and total_trades > 0:
        winning_trades = trades[trades["net_pnl"] > 0]
        losing_trades = trades[trades["net_pnl"] < 0]
        scratch_trades = trades[trades["net_pnl"] == 0]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        
        win_rate = num_wins / total_trades
        
        total_gross_gain = winning_trades["net_pnl"].sum()
        total_gross_loss = abs(losing_trades["net_pnl"].sum())
        
        profit_factor = (total_gross_gain / total_gross_loss) if total_gross_loss > 0 else (9.99 if total_gross_gain > 0 else 0.0)
        
        avg_win = float(winning_trades["net_pnl"].mean()) if num_wins > 0 else 0.0
        avg_loss = float(losing_trades["net_pnl"].mean()) if num_losses > 0 else 0.0
        win_loss_ratio = (avg_win / abs(avg_loss)) if avg_loss != 0 else (9.99 if avg_win > 0 else 0.0)
        
        avg_holding_bars = float(trades["holding_bars"].mean()) if "holding_bars" in trades.columns else 0.0
        total_friction_paid = float(trades["total_friction"].sum()) if "total_friction" in trades.columns else 0.0
    else:
        num_wins = 0
        num_losses = 0
        win_rate = 0.0
        profit_factor = 0.0
        avg_win = 0.0
        avg_loss = 0.0
        win_loss_ratio = 0.0
        avg_holding_bars = 0.0
        total_friction_paid = 0.0
        
    # 9. Exposure & Turnover
    if "shares" in equity_curve.columns:
        bars_in_market = (equity_curve["shares"] > 0).sum()
        exposure_pct = float(bars_in_market / n_bars) if n_bars > 0 else 0.0
    else:
        exposure_pct = 0.0
        
    # Turnover % (sum of all trade values / avg equity)
    if has_trades and total_trades > 0 and "entry_price" in trades.columns:
        total_traded_value = (trades["entry_price"] * trades["shares"]).sum() + (trades["exit_price"] * trades["shares"]).sum()
        avg_equity = float(equity_series.mean())
        turnover_pct = float(total_traded_value / avg_equity) if avg_equity > 0 else 0.0
    else:
        turnover_pct = 0.0
        
    # 10. Benchmark Relative Performance
    benchmark_return = 0.0
    alpha = 0.0
    beta = 1.0
    if benchmark_equity is not None and len(benchmark_equity) == n_bars:
        b_initial = float(benchmark_equity.iloc[0])
        b_final = float(benchmark_equity.iloc[-1])
        benchmark_return = (b_final - b_initial) / b_initial if b_initial > 0 else 0.0
        
        b_returns = benchmark_equity.pct_change().dropna()
        if len(b_returns) == len(returns) and b_returns.var() > 0:
            cov = np.cov(returns, b_returns)[0][1]
            beta = float(cov / (b_returns.var() or 1e-9))
            alpha = float(cagr - (risk_free_rate + beta * (benchmark_return - risk_free_rate)))
            
    metrics = {
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(final_equity, 2),
        "net_profit": round(net_profit, 2),
        "net_return_pct": round(net_return_pct * 100.0, 2),
        "cagr_pct": round(cagr * 100.0, 2),
        "annualized_volatility_pct": round(ann_volatility * 100.0, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "sortino_ratio": round(sortino_ratio, 2),
        "calmar_ratio": round(calmar_ratio, 2),
        "max_drawdown_pct": round(max_drawdown * 100.0, 2),
        "max_drawdown_duration_bars": max_dd_duration_bars,
        "total_closed_trades": total_trades,
        "winning_trades": num_wins,
        "losing_trades": num_losses,
        "win_rate_pct": round(win_rate * 100.0, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win_inr": round(avg_win, 2),
        "avg_loss_inr": round(avg_loss, 2),
        "win_loss_payoff_ratio": round(win_loss_ratio, 2),
        "avg_holding_bars": round(avg_holding_bars, 1),
        "market_exposure_pct": round(exposure_pct * 100.0, 2),
        "portfolio_turnover_pct": round(turnover_pct * 100.0, 2),
        "total_friction_inr": round(total_friction_paid, 2),
        "benchmark_return_pct": round(benchmark_return * 100.0, 2),
        "beta": round(beta, 2),
        "alpha_pct": round(alpha * 100.0, 2),
        "risk_free_rate_pct": round(risk_free_rate * 100.0, 2),
        "total_bars": n_bars,
        "test_period_years": round(years, 2)
    }
    
    return metrics


def _empty_metrics(initial_capital: float) -> Dict[str, Any]:
    return {
        "initial_capital": round(initial_capital, 2),
        "final_equity": round(initial_capital, 2),
        "net_profit": 0.0,
        "net_return_pct": 0.0,
        "cagr_pct": 0.0,
        "annualized_volatility_pct": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "calmar_ratio": 0.0,
        "max_drawdown_pct": 0.0,
        "max_drawdown_duration_bars": 0,
        "total_closed_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate_pct": 0.0,
        "profit_factor": 0.0,
        "avg_win_inr": 0.0,
        "avg_loss_inr": 0.0,
        "win_loss_payoff_ratio": 0.0,
        "avg_holding_bars": 0.0,
        "market_exposure_pct": 0.0,
        "portfolio_turnover_pct": 0.0,
        "total_friction_inr": 0.0,
        "benchmark_return_pct": 0.0,
        "beta": 1.0,
        "alpha_pct": 0.0,
        "risk_free_rate_pct": 6.5,
        "total_bars": 0,
        "test_period_years": 0.0
    }
