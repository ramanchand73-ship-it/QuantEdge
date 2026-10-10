# QuantEdge Research Report: TCS.NS Quantitative Backtest
**Document ID:** REP-SOP-QUANT-001-TCS-SMA  
**Strategy Model:** Simple Moving Average (SMA) Trend Crossover  
**Underlying Asset:** Tata Consultancy Services Ltd (`TCS.NS`)  
**Benchmark:** NIFTY 50 Index (`NIFTY_50`)  
**Simulation Period:** 2020-01-01 to 2025-12-31  
**Execution Convention:** Signal Bar $T$ Close $\rightarrow$ Execution Bar $T+1$ Open  
**Statutory Cost Model:** NSE Cash Equity Delivery (CNC) + STT + GST + Stamp Duty + Slippage  

---

## 1. Executive Summary

This study evaluates the performance of a classic dual moving average trend-following strategy on TCS.NS cash equity across a 6-year historical simulation window (2020 to 2025). The backtest was conducted using the **QuantEdge** engine adhering strictly to **SOP-QUANT-001**.

### Key Results
- **Initial Virtual Capital:** ₹10,00,000.00
- **Final Portfolio Equity:** ₹11,95,332.26
- **Net Profit:** +₹1,95,332.26 (**+19.53%**)
- **CAGR:** **+3.00%**
- **Benchmark Return (NIFTY 50 Buy & Hold):** **+23.51%**
- **Maximum Drawdown:** **36.98%**
- **Sharpe Ratio (Rf = 6.5%):** **-0.12**
- **Sortino Ratio:** **-0.14**
- **Calmar Ratio:** **0.08**

---

## 2. Trade Execution Summary

| Parameter | Observed Value |
| :--- | :--- |
| **Total Closed Trades** | 15 |
| **Winning Trades** | 6 (40.0%) |
| **Losing Trades** | 9 (60.0%) |
| **Profit Factor** | 1.62 |
| **Average Winning Trade** | ₹84,785.42 |
| **Average Losing Trade** | -₹34,820.03 |
| **Win/Loss Payoff Ratio** | 2.43 |
| **Average Holding Duration** | 48.2 trading days |
| **Total Market Friction Paid** | ₹14,248.80 (Statutory Taxes + Brokerage + Slippage) |

---

## 3. Assumptions & Methodology

1. **Order Execution Semantics:**
   - In accordance with SOP-QUANT-001, trades are **never executed at the close of the candle generating the signal**.
   - A signal produced at the Close of Day $T$ places an order filled at the Open of Day $T+1$.
   - A 5 basis point (0.05%) slippage and a 2 basis point (0.02%) half-spread penalty are applied against the trader on every entry and exit.

2. **Transaction Cost Structure:**
   - **Brokerage:** Flat ₹20 per executed order.
   - **STT:** 0.10% on both Buy and Sell turnover.
   - **Exchange Charges:** 0.00345% of turnover.
   - **SEBI Fee:** ₹10 per crore (0.0001%).
   - **Stamp Duty:** 0.015% on Buy turnover.
   - **GST:** 18% on (Brokerage + Exchange Fees + SEBI).

---

## 4. Key Quantitative Observations & Research Insights

1. **Trend Lag and Whipsaws:**
   The SMA 20/50 crossover strategy suffered from false breakouts during range-bound consolidation phases in 2021-2023, resulting in 9 losing trades. However, the high win/loss payoff ratio (2.43) ensured that sustained trends in 2020 and 2024 generated sufficient gains to produce an overall positive net PnL.
2. **Impact of Statutory Costs:**
   Total transaction costs and friction deducted ₹14,248.80 from gross performance. In higher-frequency trading, Indian statutory taxes (primarily STT and GST) represent a critical hurdle rate that can rapidly eliminate positive theoretical edge.
3. **Underperformance vs Benchmark:**
   The strategy underperformed Buy & Hold NIFTY 50 (+23.51%) because it was out of the market during key gap-up sessions (market exposure was only ~48%).

---

## 5. Limitations & Future Extensions

- **Intraday Liquidity:** Backtesting on daily bars does not model order book depth or order queuing during opening auctions.
- **Corporate Actions:** Real-world historical series must be adjusted for stock splits, bonus issues, and dividend distributions to avoid artificial price gap artifacts.
- **Recommended Next Step:** Test dynamic volatility filter (e.g. ATR breakout) or multi-asset diversification across the NIFTY 50 universe.
