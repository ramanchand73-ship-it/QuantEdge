"""Report and experiment data export module conforming to SOP-QUANT-001 (Section 12).

Provides programmatic exports for:
- Trade logs (CSV)
- Daily equity curve (CSV)
- Strategy configuration (YAML)
- Research Summary Reports (Markdown & Standalone Institutional HTML Tear Sheet)
"""

from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import pandas as pd

from src.backtesting.engine import BacktestResult


def export_trades_csv(trades_df: pd.DataFrame, output_path: Optional[Path] = None) -> str:
    """Exports trades DataFrame to CSV string or file."""
    csv_str = trades_df.to_csv(index=False)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(csv_str, encoding="utf-8")
    return csv_str


def export_equity_csv(equity_df: pd.DataFrame, output_path: Optional[Path] = None) -> str:
    """Exports equity curve DataFrame to CSV string or file."""
    csv_str = equity_df.to_csv(index=True)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(csv_str, encoding="utf-8")
    return csv_str


def export_config_yaml(config_dict: Dict[str, Any], output_path: Optional[Path] = None) -> str:
    """Serializes backtest configuration to YAML."""
    yaml_str = yaml.dump(config_dict, sort_keys=False, default_flow_style=False)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(yaml_str, encoding="utf-8")
    return yaml_str


def generate_markdown_report(result: BacktestResult, metrics: Dict[str, Any]) -> str:
    """Generates an institutional research report in GitHub-flavored Markdown."""
    md = f"""# QuantEdge Strategy Research Report
**Document ID:** REP-{result.strategy_name.upper()}-{result.symbol.replace('.', '_')}  
**Conforms to:** SOP-QUANT-001 (Historical Backtesting Engine)  
**Execution Mode:** Historical Simulation (Paper Trading Only)  
**Disclaimer:** All results are simulated based on historical market prices and execution assumptions. Past performance is strictly non-indicative of future returns.

---

## 1. Executive Summary
- **Strategy:** `{result.strategy_name}`
- **Instrument:** `{result.symbol}`
- **Simulation Period:** `{result.start_date}` to `{result.end_date}`
- **Initial Capital:** ₹{metrics.get('initial_capital', 0):,.2f}
- **Final Portfolio Equity:** ₹{metrics.get('final_equity', 0):,.2f}
- **Net Profit / (Loss):** ₹{metrics.get('net_profit', 0):,.2f} (**{metrics.get('net_return_pct', 0):.2f}%**)
- **CAGR:** **{metrics.get('cagr_pct', 0):.2f}%**
- **Benchmark Return:** **{metrics.get('benchmark_return_pct', 0):.2f}%**

---

## 2. Key Performance Indicators (KPIs)

| Metric | Strategy Value | Benchmark / Notes |
| :--- | :--- | :--- |
| **CAGR** | {metrics.get('cagr_pct', 0):.2f}% | Annualized geometric return |
| **Annualized Volatility** | {metrics.get('annualized_volatility_pct', 0):.2f}% | Annualized daily return std |
| **Sharpe Ratio (Rf=6.5%)**| {metrics.get('sharpe_ratio', 0):.2f} | Risk-adjusted excess return |
| **Sortino Ratio** | {metrics.get('sortino_ratio', 0):.2f} | Downside risk-adjusted ratio |
| **Calmar Ratio** | {metrics.get('calmar_ratio', 0):.2f} | CAGR / Maximum Drawdown |
| **Maximum Drawdown** | **{metrics.get('max_drawdown_pct', 0):.2f}%** | Peak-to-trough decline |
| **Max Drawdown Duration**| {metrics.get('max_drawdown_duration_bars', 0)} bars | Recovery length |
| **Market Exposure** | {metrics.get('market_exposure_pct', 0):.2f}% | Time spent invested |
| **Beta vs Benchmark** | {metrics.get('beta', 1.0):.2f} | Systematic market sensitivity |
| **Alpha (Annualized)** | {metrics.get('alpha_pct', 0):.2f}% | Excess return over CAPM |

---

## 3. Trade Analysis & Order Execution

| Trade Metric | Value |
| :--- | :--- |
| **Total Closed Trades** | {metrics.get('total_closed_trades', 0)} |
| **Winning Trades** | {metrics.get('winning_trades', 0)} ({metrics.get('win_rate_pct', 0):.1f}%) |
| **Losing Trades** | {metrics.get('losing_trades', 0)} |
| **Profit Factor** | {metrics.get('profit_factor', 0):.2f} |
| **Average Win** | ₹{metrics.get('avg_win_inr', 0):,.2f} |
| **Average Loss** | ₹{metrics.get('avg_loss_inr', 0):,.2f} |
| **Win/Loss Payoff Ratio**| {metrics.get('win_loss_payoff_ratio', 0):.2f} |
| **Average Holding Period** | {metrics.get('avg_holding_bars', 0):.1f} bars |
| **Total Friction (Costs + Slippage)** | ₹{metrics.get('total_friction_inr', 0):,.2f} |

---

## 4. Execution Assumptions & Cost Model
- **Cost Model:** `{result.execution_assumptions.get('cost_model')}`
- **Execution Timing:** Signal at Bar $T$ Close $\\rightarrow$ Fill at Bar $T+1$ Open (Delay = {result.execution_assumptions.get('signal_delay_bars')} bar)
- **Slippage Assumed:** {result.execution_assumptions.get('slippage_bps')} bps
- **Position Allocation:** {result.execution_assumptions.get('allocation_pct', 0.95)*100:.0f}% of available equity
- **Stop Loss:** {result.execution_assumptions.get('stop_loss_pct') or 'Disabled'}
- **Take Profit:** {result.execution_assumptions.get('take_profit_pct') or 'Disabled'}

---

## 5. Strategy Parameters
```yaml
{yaml.dump(result.strategy_params, default_flow_style=False)}
```

---

## 6. Regulatory & Operational Risk Warnings
1. **Model Limitations:** OHLCV bar backtesting cannot fully reconstruct intrabar order book depth, liquidity voids, or queue priority.
2. **Statutory Taxes:** Indian market transaction costs (STT, Stamp Duty, GST, Exchange fees) significantly erode active trading alpha.
3. **Execution Delay:** Instantaneous close fills suffer severe look-ahead bias; this engine strictly delays execution to the next bar open.
"""
    return md


def generate_html_tear_sheet(result: BacktestResult, metrics: Dict[str, Any]) -> str:
    """Generates a standalone, beautifully styled HTML tear-sheet report."""
    md_content = generate_markdown_report(result, metrics)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuantEdge Research Tear Sheet: {result.strategy_name} ({result.symbol})</title>
<style>
  :root {{
    --bg: #0F172A;
    --card-bg: #1E293B;
    --border: #334155;
    --text: #F8FAFC;
    --text-muted: #94A3B8;
    --primary: #10B981;
    --accent: #3B82F6;
    --danger: #EF4444;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background-color: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 2.5rem;
    line-height: 1.6;
  }}
  .container {{
    max-width: 1000px;
    margin: 0 auto;
  }}
  .header {{
    border-bottom: 2px solid var(--border);
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
  }}
  .badge {{
    background: #064E3B;
    color: #34D399;
    padding: 0.3rem 0.8rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    display: inline-block;
  }}
  h1 {{ margin: 0.5rem 0 0.2rem 0; font-size: 2rem; }}
  .subtitle {{ color: var(--text-muted); font-size: 0.95rem; margin-bottom: 1rem; }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .kpi-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    padding: 1.2rem;
  }}
  .kpi-label {{ color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; }}
  .kpi-val {{ font-size: 1.6rem; font-weight: 700; color: #FFFFFF; margin-top: 0.2rem; }}
  .kpi-val.green {{ color: var(--primary); }}
  .kpi-val.red {{ color: var(--danger); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    background: var(--card-bg);
    border-radius: 0.5rem;
    overflow: hidden;
  }}
  th, td {{
    padding: 0.8rem 1.2rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  th {{ background: #111827; color: var(--text-muted); font-size: 0.85rem; }}
  .footer {{
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    font-size: 0.8rem;
    color: var(--text-muted);
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <span class="badge">SOP-QUANT-001 VERIFIED</span>
    <h1>QuantEdge Strategy Tear Sheet</h1>
    <div class="subtitle">Strategy: <strong>{result.strategy_name}</strong> | Instrument: <strong>{result.symbol}</strong> | Period: {result.start_date} &rarr; {result.end_date}</div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Final Equity</div>
      <div class="kpi-val green">₹{metrics.get('final_equity', 0):,.2f}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Net Return (CAGR)</div>
      <div class="kpi-val green">{metrics.get('cagr_pct', 0):.2f}%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Sharpe Ratio (Rf=6.5%)</div>
      <div class="kpi-val">{metrics.get('sharpe_ratio', 0):.2f}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Max Drawdown</div>
      <div class="kpi-val red">{metrics.get('max_drawdown_pct', 0):.2f}%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-val">{metrics.get('win_rate_pct', 0):.1f}%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Profit Factor</div>
      <div class="kpi-val">{metrics.get('profit_factor', 0):.2f}</div>
    </div>
  </div>

  <h2>Performance Analytics</h2>
  <table>
    <tr><th>Metric</th><th>Strategy Value</th><th>Description</th></tr>
    <tr><td>Compound Annual Growth Rate (CAGR)</td><td><strong>{metrics.get('cagr_pct', 0):.2f}%</strong></td><td>Annualized geometric rate of return</td></tr>
    <tr><td>Annualized Volatility</td><td>{metrics.get('annualized_volatility_pct', 0):.2f}%</td><td>Standard deviation of periodic returns scaled to 252 bars</td></tr>
    <tr><td>Sortino Ratio</td><td>{metrics.get('sortino_ratio', 0):.2f}</td><td>Excess return divided by downside deviation</td></tr>
    <tr><td>Calmar Ratio</td><td>{metrics.get('calmar_ratio', 0):.2f}</td><td>CAGR divided by Maximum Drawdown</td></tr>
    <tr><td>Total Closed Trades</td><td>{metrics.get('total_closed_trades', 0)}</td><td>Winning: {metrics.get('winning_trades', 0)} | Losing: {metrics.get('losing_trades', 0)}</td></tr>
    <tr><td>Average Trade Win / Loss</td><td>₹{metrics.get('avg_win_inr', 0):,.2f} / ₹{metrics.get('avg_loss_inr', 0):,.2f}</td><td>Payoff ratio: {metrics.get('win_loss_payoff_ratio', 0):.2f}</td></tr>
    <tr><td>Market Exposure</td><td>{metrics.get('market_exposure_pct', 0):.2f}%</td><td>Percentage of backtest duration with open position</td></tr>
    <tr><td>Total Friction Paid</td><td>₹{metrics.get('total_friction_inr', 0):,.2f}</td><td>Brokerage, STT, Exchange fees, GST, Stamp Duty, Slippage</td></tr>
    <tr><td>Benchmark Return</td><td>{metrics.get('benchmark_return_pct', 0):.2f}%</td><td>Buy & Hold return over identical period</td></tr>
  </table>

  <div class="footer">
    <p><strong>Disclaimer:</strong> Strictly for quantitative research and educational evaluation. Simulation does not account for intraday depth slippage, execution latency spikes, or exchange liquidity shocks. Past simulated results are non-predictive of live market profitability.</p>
  </div>
</div>
</body>
</html>"""
    return html
