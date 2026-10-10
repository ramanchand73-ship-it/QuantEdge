# QuantEdge Strategy Research Report
**Document ID:** REP-SMA_CROSSOVER-TCS_NS  
**Conforms to:** SOP-QUANT-001 (Historical Backtesting Engine)  
**Execution Mode:** Historical Simulation (Paper Trading Only)  
**Disclaimer:** All results are simulated based on historical market prices and execution assumptions. Past performance is strictly non-indicative of future returns.

---

## 1. Executive Summary
- **Strategy:** `sma_crossover`
- **Instrument:** `TCS.NS`
- **Simulation Period:** `2020-01-01 00:00:00` to `2025-12-31 00:00:00`
- **Initial Capital:** ₹1,000,000.00
- **Final Portfolio Equity:** ₹1,195,332.26
- **Net Profit / (Loss):** ₹195,332.26 (**19.53%**)
- **CAGR:** **2.91%**
- **Benchmark Return:** **23.51%**

---

## 2. Key Performance Indicators (KPIs)

| Metric | Strategy Value | Benchmark / Notes |
| :--- | :--- | :--- |
| **CAGR** | 2.91% | Annualized geometric return |
| **Annualized Volatility** | 14.55% | Annualized daily return std |
| **Sharpe Ratio (Rf=6.5%)**| -0.16 | Risk-adjusted excess return |
| **Sortino Ratio** | -0.30 | Downside risk-adjusted ratio |
| **Calmar Ratio** | 0.08 | CAGR / Maximum Drawdown |
| **Maximum Drawdown** | **38.38%** | Peak-to-trough decline |
| **Max Drawdown Duration**| 973 bars | Recovery length |
| **Market Exposure** | 47.70% | Time spent invested |
| **Beta vs Benchmark** | 0.00 | Systematic market sensitivity |
| **Alpha (Annualized)** | -3.63% | Excess return over CAPM |

---

## 3. Trade Analysis & Order Execution

| Trade Metric | Value |
| :--- | :--- |
| **Total Closed Trades** | 15 |
| **Winning Trades** | 5 (33.3%) |
| **Losing Trades** | 10 |
| **Profit Factor** | 1.37 |
| **Average Win** | ₹130,402.35 |
| **Average Loss** | ₹-47,517.05 |
| **Win/Loss Payoff Ratio**| 2.74 |
| **Average Holding Period** | 49.8 bars |
| **Total Friction (Costs + Slippage)** | ₹48,685.48 |

---

## 4. Execution Assumptions & Cost Model
- **Cost Model:** `nse_equity_delivery`
- **Execution Timing:** Signal at Bar $T$ Close $\rightarrow$ Fill at Bar $T+1$ Open (Delay = 1 bar)
- **Slippage Assumed:** 5.0 bps
- **Position Allocation:** 95% of available equity
- **Stop Loss:** Disabled
- **Take Profit:** Disabled

---

## 5. Strategy Parameters
```yaml
fast_period: 20
slow_period: 50
trade_direction: long_only

```

---

## 6. Regulatory & Operational Risk Warnings
1. **Model Limitations:** OHLCV bar backtesting cannot fully reconstruct intrabar order book depth, liquidity voids, or queue priority.
2. **Statutory Taxes:** Indian market transaction costs (STT, Stamp Duty, GST, Exchange fees) significantly erode active trading alpha.
3. **Execution Delay:** Instantaneous close fills suffer severe look-ahead bias; this engine strictly delays execution to the next bar open.
