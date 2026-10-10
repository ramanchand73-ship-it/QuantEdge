# QuantEdge: NSE Quantitative Trading & Historical Backtesting Engine

**Standard Operating Procedure ID:** SOP-QUANT-001  
**Target Market:** National Stock Exchange of India (NSE)  
**Supported Asset Classes:** Cash Equity (CNC / Delivery & MIS / Intraday)  
**Execution Mode:** Historical Simulation & Paper Research Only (*Live Broker Trading is Permanently Disabled*)

---

## 1. Overview & Architecture

QuantEdge is an institutional-grade quantitative research framework and backtesting engine engineered in Python. It simulates algorithmic trading strategies on historical NSE market data with deterministic execution semantics, real-world Indian statutory taxes, exchange fees, slippage modeling, and rigorous look-ahead bias elimination.

```
QuantEdge/
├── config/                      # Strategy & statutory cost models (YAML)
│   ├── nse_cost_models.yaml     # Delivery, Intraday, and Ideal cost structures
│   ├── strategy_sma_crossover.yaml
│   ├── strategy_rsi.yaml
│   └── backtest_tcs_nifty50_template.yaml
├── data/
│   ├── raw/                     # Original imported market data (CSV)
│   ├── processed/               # Clean, validated datasets (Parquet / CSV)
│   └── sample/                  # Small synthetic datasets (TCS.NS, NIFTY 50)
├── src/
│   ├── data/                    # Ingestion, validation & synthetic data generation
│   │   ├── loader.py            # CSV ingestion & validation wrapper
│   │   ├── validator.py         # OHLC geometry, missing value & non-positive price checks
│   │   ├── preprocessor.py      # Chronological Train/Val/OOS & Walk-Forward splitting
│   │   └── synthetic.py         # Geometric Brownian Motion & edge-case data generators
│   ├── strategies/              # Reusable quantitative strategies
│   │   ├── base.py              # BaseStrategy abstract interface & parameter schema
│   │   ├── sma_crossover.py     # Strategy A: Fast & Slow SMA Crossover
│   │   ├── rsi_strategy.py      # Strategy B: Wilder's RSI Mean-Reversion / Momentum
│   │   └── registry.py          # Dynamic strategy discovery registry
│   ├── backtesting/             # Deterministic simulation engine & portfolio math
│   │   ├── costs.py             # Brokerage, STT, Exchange fees, SEBI, GST, Stamp Duty, Slippage
│   │   ├── order.py             # Order & Trade lifecycle objects
│   │   ├── portfolio.py         # Mark-to-market accounting, cash ledger, drawdown tracking
│   │   └── engine.py            # Event-driven / bar-by-bar execution loop (Bar T Close -> Bar T+1 Open)
│   ├── risk/                    # Institutional risk & performance analytics
│   │   ├── metrics.py           # CAGR, Sharpe, Sortino, Calmar, MaxDD, Win Rate, Turnover
│   │   └── risk_manager.py      # Drawdown caps & position limits
│   ├── reporting/               # Financial charts and institutional tear-sheet exports
│   │   ├── charts.py            # Interactive Plotly candlestick, equity curve & drawdown
│   │   └── exporter.py          # CSV logs, YAML configs, Markdown & HTML tear-sheet generator
│   └── dashboard/               # High-performance Streamlit research UI
│       └── app.py               # Interactive research dashboard
├── tests/                       # Automated test suite (pytest)
│   ├── test_data_validation.py  # Data checks, duplicate detection & error auditing
│   ├── test_strategies.py       # Strategy parameter bounds & signal generation
│   ├── test_lookahead_bias.py   # Future price mutation & order timing tests
│   ├── test_transaction_costs.py# NSE fee formulas & slippage direction
│   ├── test_portfolio_accounting.py # Cash balance conservation & negative cash guards
│   ├── test_performance_metrics.py  # Edge-case zero-division & statistical metrics
│   └── test_reproducibility.py  # 100% deterministic simulation verification
├── reports/                     # Pre-generated research reports & trade logs
├── notebooks/                   # Exploratory research scripts
├── requirements.txt             # Pinned project dependencies
├── .env.example                 # Safe environment configuration template
└── README.md                    # System documentation
```

---

## 2. Key Features

- **Strict Look-Ahead Protection:** Indicators strictly utilize causal historical windows. Orders generated from signals at Bar $T$ Close execute deterministically at **Bar $T+1$ Open**, completely eliminating close-to-close fill bias.
- **NSE Statutory Cost & Slippage Engine:** Configurable Indian market friction models:
  - Brokerage: Percentage or capped flat fee (e.g. ₹20 per order).
  - Securities Transaction Tax (STT): 0.1% on delivery turnover or 0.025% on intraday sell.
  - Exchange Transaction Charges (NSE): 0.00345%.
  - SEBI Turnover Fee: ₹10 per crore (0.0001%).
  - Stamp Duty: 0.015% on Buy turnover.
  - Goods and Services Tax (GST): 18% on (Brokerage + Exchange Fees + SEBI charges).
  - Configurable Bid-Ask Spread and Market Slippage in basis points.
- **Robust Data Validation:** Enforces strict OHLC geometric invariants ($High \ge \max(Open, Close)$, $Low \le \min(Open, Close)$, $High \ge Low$), rejects non-positive prices, flags duplicates, sorts chronologically, and logs transparent data quality warnings without silently fabricating prices.
- **Portfolio Capital Protection:** Rejects orders if total required cash (turnover + statutory fees) exceeds available cash balance.
- **Interactive Streamlit Dashboard:** Modern dark glassmorphic interface with interactive Plotly equity curves, underwater drawdowns, trade candlestick markers, trade history logs, and instant HTML/CSV/YAML exports.

---

## 3. Installation & Setup

### Prerequisites
- Python 3.11, 3.12, or 3.13 (64-bit)

### Windows Setup Instructions

```powershell
# 1. Navigate to the project root
cd d:\QuantEdge

# 2. Create an isolated virtual environment (if not already created)
py -3 -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install pinned dependencies
.\.venv\Scripts\pip.exe install -r requirements.txt
```

---

## 4. Running the Application

### Launch the Streamlit Research Dashboard
```powershell
.\.venv\Scripts\streamlit.exe run src/dashboard/app.py
```
Open your browser at `http://localhost:8501`.

### Run Interactive Strategy Exploration Script
```powershell
.\.venv\Scripts\python.exe notebooks/01_strategy_exploration.py
```

### Re-generate Synthetic Datasets
```powershell
.\.venv\Scripts\python.exe -c "from src.data.synthetic import save_default_sample_datasets; save_default_sample_datasets('data/sample')"
```

---

## 5. Running Automated Tests

Run the full automated test suite verifying data validation, indicator logic, look-ahead bias immunity, transaction fee math, and simulation determinism:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Expected output:
```
============================= test session starts =============================
collected 22 items
tests/test_data_validation.py::test_valid_market_data_passes PASSED
tests/test_data_validation.py::test_negative_or_zero_price_rejected PASSED
tests/test_data_validation.py::test_invalid_ohlc_relationships_rejected PASSED
tests/test_data_validation.py::test_duplicate_and_unsorted_timestamps_handled PASSED
tests/test_data_validation.py::test_empty_dataset_rejected PASSED
tests/test_data_validation.py::test_nan_handling_without_silent_fabrication PASSED
tests/test_lookahead_bias.py::test_sma_no_lookahead_on_future_mutation PASSED
tests/test_lookahead_bias.py::test_rsi_no_lookahead_on_future_mutation PASSED
tests/test_lookahead_bias.py::test_order_timing_executes_at_t_plus_1_open PASSED
tests/test_performance_metrics.py::test_zero_trades_edge_case PASSED
tests/test_performance_metrics.py::test_positive_trade_metrics PASSED
tests/test_portfolio_accounting.py::test_portfolio_cash_accounting PASSED
tests/test_portfolio_accounting.py::test_insufficient_cash_rejection PASSED
tests/test_reproducibility.py::test_simulation_reproducibility PASSED
tests/test_strategies.py::test_sma_parameter_validation PASSED
tests/test_strategies.py::test_sma_signal_generation_on_trend PASSED
tests/test_strategies.py::test_rsi_parameter_validation PASSED
tests/test_strategies.py::test_rsi_bounds_and_oscillating_signals PASSED
tests/test_strategies.py::test_strategy_registry_discovery PASSED
tests/test_transaction_costs.py::test_nse_equity_delivery_cost_breakdown PASSED
tests/test_transaction_costs.py::test_slippage_and_spread_direction PASSED
tests/test_transaction_costs.py::test_zero_cost_model PASSED
============================= 22 passed in 2.20s ==============================
```

---

## 6. How to Run Your First Backtest

1. Start the Streamlit dashboard: `.\.venv\Scripts\streamlit.exe run src/dashboard/app.py`.
2. In the sidebar:
   - **Data Ingestion:** Select `TCS.NS (Sample Daily 2020-2025)` or upload your own historical CSV (`date, open, high, low, close, volume`).
   - **Date Range:** Adjust start and end dates.
   - **Strategy:** Choose `SMA Crossover Trend Strategy` or `Relative Strength Index (RSI) Oscillator`.
   - **Parameters:** Tune moving average windows or RSI thresholds using dynamic sliders.
   - **Cost Model:** Select `NSE Cash Delivery` (with STT, GST, Stamp Duty) or `Zero Cost Ideal`.
   - **Slippage:** Set execution slippage (e.g. 5 bps).
3. The dashboard recalculates and renders:
   - Metric cards: Final Equity, CAGR, Sharpe Ratio, Max Drawdown, Win Rate.
   - Interactive Plotly equity curves overlaid with NIFTY 50 benchmark.
   - Drawdown underwater chart.
   - Candlestick price chart with actual green Buy triangles and red Sell triangles.
   - Complete trade ledger and order audit logs.
4. Navigate to the **Export & Reproducibility** tab to download:
   - Completed trades log (`.csv`)
   - Daily mark-to-market equity curve (`.csv`)
   - Standalone research tear sheet (`.html`)
   - Reproducible experiment configuration (`.yaml`)

---

## 7. Known Assumptions & Research Limitations

1. **OHLCV Candlestick Granularity:** Daily and candle-based backtests cannot reconstruct order book queue priority or intrabar market impact.
2. **Statutory Tax Drag:** Frequent trading on Indian cash equity carries substantial drag due to STT (0.1%), stamp duty, and GST on brokerage/exchange fees.
3. **Execution Latency:** QuantEdge assumes orders generated at Bar $T$ Close fill at Bar $T+1$ Open. Extreme opening gaps or limit-up/limit-down circuit breakers are not guaranteed to fill in live conditions.
4. **No Financial Advice:** This platform is strictly for quantitative research, academic evaluation, and paper backtesting.
