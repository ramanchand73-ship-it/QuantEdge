"""QuantEdge - Institutional Quantitative Research & Historical Backtesting Dashboard.

Conforms to SOP-QUANT-001 (Section 12: Dashboard Requirements).
Built with Streamlit and Plotly for deep visual analysis, interactive parameter tuning,
data quality auditing, and reproducible strategy research.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import io
import yaml
import streamlit as st
import pandas as pd
import numpy as np

from src.data.loader import load_csv_data
from src.data.validator import validate_market_data, DataValidationResult
from src.data.synthetic import generate_synthetic_ohlcv
from src.strategies.registry import list_strategies, get_strategy
from src.backtesting.costs import load_cost_model, CostModel
from src.backtesting.engine import BacktestEngine, BacktestResult
from src.risk.metrics import calculate_performance_metrics
from src.reporting.charts import (
    create_equity_curve_chart,
    create_drawdown_chart,
    create_candlestick_trade_chart
)
from src.reporting.exporter import (
    export_trades_csv,
    export_equity_csv,
    export_config_yaml,
    generate_markdown_report,
    generate_html_tear_sheet
)

# Set page config
st.set_page_config(
    page_title="QuantEdge | NSE Backtesting Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Styling (Dark Glassmorphic Institutional Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container background */
    .stApp {
        background: radial-gradient(circle at 10% 20%, #0d1527 0%, #070b14 100%);
        color: #F8FAFC;
    }
    
    /* Header hero styling */
    .hero-container {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(8px);
    }
    
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        background: linear-gradient(90deg, #10B981, #38BDF8, #818CF8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    
    .hero-subtitle {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-top: 0.3rem;
    }
    
    /* Metric Cards */
    .kpi-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: rgba(56, 189, 248, 0.4);
    }
    
    .kpi-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #94A3B8;
        letter-spacing: 0.8px;
        font-weight: 600;
    }
    
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-top: 0.25rem;
        font-feature-settings: "tnum";
    }
    
    .kpi-sub {
        font-size: 0.78rem;
        margin-top: 0.2rem;
    }
    
    .text-green { color: #10B981 !important; }
    .text-red { color: #EF4444 !important; }
    .text-blue { color: #38BDF8 !important; }
    .text-amber { color: #F59E0B !important; }
    
    /* Badge tag */
    .compliance-badge {
        display: inline-block;
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def load_dataset_source(selection: str, uploaded_file) -> pd.DataFrame:
    """Helper to load data based on user selection in sidebar."""
    if selection == "Upload CSV File" and uploaded_file is not None:
        raw_df, res = load_csv_data(uploaded_file)
        if not res.is_valid:
            st.error(f"Data validation failed: {res.errors}")
            return pd.DataFrame()
        return res.clean_data
        
    elif selection == "TCS.NS (Sample Daily 2020-2025)":
        p = Path("data/sample/tcs_sample_daily.csv")
        if not p.exists():
            from src.data.synthetic import save_default_sample_datasets
            save_default_sample_datasets("data/sample")
        _, res = load_csv_data(p, source_name="TCS.NS Daily")
        return res.clean_data or pd.DataFrame()
        
    elif selection == "NIFTY 50 Index (Sample Daily)":
        p = Path("data/sample/nifty50_sample_daily.csv")
        if not p.exists():
            from src.data.synthetic import save_default_sample_datasets
            save_default_sample_datasets("data/sample")
        _, res = load_csv_data(p, source_name="NIFTY 50 Daily")
        return res.clean_data or pd.DataFrame()
        
    return pd.DataFrame()


def main():
    # Hero Banner
    st.markdown("""
    <div class="hero-container">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 class="hero-title">QuantEdge Engine</h1>
                <div class="hero-subtitle">Institutional Quantitative Strategy Simulation & Historical Risk Engine &bull; NSE India Cash Equity</div>
            </div>
            <div>
                <span class="compliance-badge">SOP-QUANT-001 COMPLIANT</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar: Setup & Parameters
    st.sidebar.markdown("### 1. Market Data Ingestion")
    data_option = st.sidebar.selectbox(
        "Select Historical Dataset",
        ["TCS.NS (Sample Daily 2020-2025)", "NIFTY 50 Index (Sample Daily)", "Upload CSV File"]
    )
    
    uploaded_file = None
    if data_option == "Upload CSV File":
        uploaded_file = st.sidebar.file_uploader(
            "Upload OHLCV CSV (date, open, high, low, close, volume)",
            type=["csv"]
        )
        
    df = load_dataset_source(data_option, uploaded_file)
    
    if df.empty:
        st.warning("Please upload a valid CSV or select a sample dataset from the sidebar to begin.")
        return

    # Date range filtering in sidebar
    min_date = df.index.min().date()
    max_date = df.index.max().date()
    
    date_range = st.sidebar.date_input(
        "Simulation Date Range",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    start_filter = str(date_range[0]) if len(date_range) > 0 else str(min_date)
    end_filter = str(date_range[1]) if len(date_range) > 1 else str(max_date)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 2. Strategy Configuration")
    
    strategies_info = list_strategies()
    strategy_names = list(strategies_info.keys())
    selected_strat_key = st.sidebar.selectbox(
        "Strategy Model",
        strategy_names,
        format_func=lambda k: strategies_info[k]["display_name"]
    )
    
    selected_strat_meta = strategies_info[selected_strat_key]
    st.sidebar.caption(selected_strat_meta["description"])
    
    # Dynamic strategy parameter controls
    param_schema = selected_strat_meta["parameter_schema"]
    user_params = {}
    
    for param_name, schema in param_schema.items():
        p_type = schema["type"]
        default_val = schema["default"]
        desc = schema["description"]
        
        if p_type == "int":
            user_params[param_name] = st.sidebar.slider(
                f"{param_name.replace('_', ' ').title()}",
                min_value=schema.get("min", 1),
                max_value=schema.get("max", 200),
                value=int(default_val),
                step=schema.get("step", 1),
                help=desc
            )
        elif p_type == "float":
            user_params[param_name] = st.sidebar.slider(
                f"{param_name.replace('_', ' ').title()}",
                min_value=float(schema.get("min", 0.0)),
                max_value=float(schema.get("max", 100.0)),
                value=float(default_val),
                step=float(schema.get("step", 0.5)),
                help=desc
            )
        elif p_type == "choice":
            user_params[param_name] = st.sidebar.selectbox(
                f"{param_name.replace('_', ' ').title()}",
                options=schema.get("options", []),
                index=0,
                help=desc
            )
        elif p_type == "bool":
            user_params[param_name] = st.sidebar.checkbox(
                f"{param_name.replace('_', ' ').title()}",
                value=bool(default_val),
                help=desc
            )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 3. Execution & Portfolio Settings")
    
    initial_cap = st.sidebar.number_input(
        "Initial Virtual Capital (INR)",
        min_value=10000.0,
        max_value=100000000.0,
        value=1000000.0,
        step=50000.0,
        format="%.0f"
    )
    
    cost_model_choice = st.sidebar.selectbox(
        "Statutory Cost Model",
        ["nse_equity_delivery", "nse_equity_intraday", "zero_cost_ideal"],
        format_func=lambda x: "NSE Cash Delivery (CNC + STT + GST)" if x == "nse_equity_delivery" else (
            "NSE Cash Intraday (MIS + ₹20 cap)" if x == "nse_equity_intraday" else "Zero Cost Ideal Benchmark"
        )
    )
    
    slippage_bps = st.sidebar.slider(
        "Execution Slippage (bps)",
        min_value=0.0,
        max_value=50.0,
        value=5.0,
        step=1.0,
        help="Basis points added to buy price and deducted from sell price (1 bps = 0.01%)."
    )
    
    enable_risk_stops = st.sidebar.checkbox("Enable Stop-Loss & Take-Profit", value=False)
    stop_loss_pct = None
    take_profit_pct = None
    if enable_risk_stops:
        sl_val = st.sidebar.slider("Stop Loss %", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
        tp_val = st.sidebar.slider("Take Profit %", min_value=1.0, max_value=50.0, value=10.0, step=1.0)
        stop_loss_pct = sl_val / 100.0
        take_profit_pct = tp_val / 100.0

    # Load benchmark data (NIFTY 50)
    nifty_path = Path("data/sample/nifty50_sample_daily.csv")
    benchmark_df = None
    if nifty_path.exists():
        _, b_res = load_csv_data(nifty_path, source_name="NIFTY 50")
        if b_res.is_valid:
            benchmark_df = b_res.clean_data

    # Instantiate Strategy & Backtest Engine
    try:
        strategy_instance = get_strategy(selected_strat_key, user_params)
        cost_model = load_cost_model(cost_model_choice)
        
        engine = BacktestEngine(
            strategy=strategy_instance,
            cost_model=cost_model,
            initial_capital=initial_cap,
            allocation_pct=0.95,
            signal_delay_bars=1,
            slippage_bps=slippage_bps,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        
        result = engine.run(
            data=df,
            benchmark_data=benchmark_df,
            start_date=start_filter,
            end_date=end_filter
        )
        
        metrics = calculate_performance_metrics(
            equity_curve=result.equity_curve,
            trades=result.trades,
            initial_capital=result.initial_capital,
            benchmark_equity=result.benchmark_equity
        )
        
    except Exception as e:
        st.error(f"Error during simulation execution: {e}")
        return

    # Render KPI Cards Grid
    col1, col2, col3, col4, col5 = st.columns(5)
    
    net_ret = metrics.get('net_return_pct', 0)
    net_ret_class = "text-green" if net_ret >= 0 else "text-red"
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Final Equity</div>
            <div class="kpi-value">₹{metrics.get('final_equity', 0):,.0f}</div>
            <div class="kpi-sub {net_ret_class}">Net Return: {net_ret:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        cagr = metrics.get('cagr_pct', 0)
        cagr_class = "text-green" if cagr >= 0 else "text-red"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">CAGR (Ann. Return)</div>
            <div class="kpi-value {cagr_class}">{cagr:.2f}%</div>
            <div class="kpi-sub" style="color: #94A3B8;">Benchmark: {metrics.get('benchmark_return_pct', 0):+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Sharpe Ratio</div>
            <div class="kpi-value text-blue">{metrics.get('sharpe_ratio', 0):.2f}</div>
            <div class="kpi-sub" style="color: #94A3B8;">Sortino: {metrics.get('sortino_ratio', 0):.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Max Drawdown</div>
            <div class="kpi-value text-red">{metrics.get('max_drawdown_pct', 0):.2f}%</div>
            <div class="kpi-sub" style="color: #94A3B8;">Duration: {metrics.get('max_drawdown_duration_bars', 0)} bars</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Win Rate & Trades</div>
            <div class="kpi-value">{metrics.get('win_rate_pct', 0):.1f}%</div>
            <div class="kpi-sub" style="color: #94A3B8;">{metrics.get('total_closed_trades', 0)} Trades (PF: {metrics.get('profit_factor', 0):.2f})</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # Main Tabs
    tab_overview, tab_trades, tab_tearsheet, tab_data_audit, tab_export = st.tabs([
        "📈 Overview & Charts",
        "📋 Trade History & Execution Log",
        "📊 Quantitative Risk Tear Sheet",
        "🛡️ Data Quality & Audit",
        "💾 Export & Reproducibility"
    ])

    with tab_overview:
        col_chart_l, col_chart_r = st.columns([2, 1])
        
        with col_chart_l:
            st.plotly_chart(
                create_equity_curve_chart(result.equity_curve, result.benchmark_equity),
                use_container_width=True
            )
            st.plotly_chart(
                create_drawdown_chart(result.equity_curve),
                use_container_width=True
            )
            
        with col_chart_r:
            st.markdown("#### Simulation Assumptions")
            st.info(f"""
            - **Signal Latency:** Signal at Bar $T$ Close &rarr; Fill at Bar $T+1$ Open (Delay = 1 bar)
            - **Statutory Model:** `{result.execution_assumptions.get('cost_model')}`
            - **Slippage Impact:** {result.execution_assumptions.get('slippage_bps')} bps
            - **Total Friction Incurred:** ₹{metrics.get('total_friction_inr', 0):,.2f}
            - **Rejected Orders:** {len(result.rejected_orders)}
            """)
            
            st.markdown("#### Risk & Trade Metrics")
            st.markdown(f"""
            - **Annualized Volatility:** {metrics.get('annualized_volatility_pct', 0):.2f}%
            - **Calmar Ratio:** {metrics.get('calmar_ratio', 0):.2f}
            - **Market Exposure:** {metrics.get('market_exposure_pct', 0):.2f}%
            - **Portfolio Turnover:** {metrics.get('portfolio_turnover_pct', 0):.2f}%
            - **Beta vs Benchmark:** {metrics.get('beta', 1.0):.2f}
            - **Alpha (Annualized):** {metrics.get('alpha_pct', 0):.2f}%
            """)
            
        st.markdown("---")
        st.subheader("Price Action, Technical Indicators & Executed Trades")
        st.plotly_chart(
            create_candlestick_trade_chart(result.data_with_signals, result.trades),
            use_container_width=True
        )

    with tab_trades:
        st.subheader("Completed Round-Trip Trades")
        if not result.trades.empty:
            st.dataframe(
                result.trades.style.format({
                    "entry_price": "₹{:.2f}",
                    "exit_price": "₹{:.2f}",
                    "gross_pnl": "₹{:,.2f}",
                    "net_pnl": "₹{:,.2f}",
                    "return_pct": "{:.2%}",
                    "total_friction": "₹{:.2f}"
                }),
                use_container_width=True
            )
        else:
            st.info("No trades executed during the selected test period.")
            
        if result.rejected_orders:
            st.markdown("---")
            st.subheader("Rejected Orders Audit Log")
            rej_data = [
                {
                    "order_id": o.order_id,
                    "timestamp": str(o.created_time),
                    "action": o.action,
                    "shares": o.shares,
                    "reason": o.rejection_reason
                }
                for o in result.rejected_orders
            ]
            st.dataframe(pd.DataFrame(rej_data), use_container_width=True)

    with tab_tearsheet:
        st.subheader("Comprehensive Quantitative Risk Report")
        tearsheet_cols = st.columns(2)
        
        with tearsheet_cols[0]:
            st.markdown("#### Return & Risk Characteristics")
            st.table(pd.DataFrame([
                {"Metric": "Initial Capital", "Value": f"₹{metrics['initial_capital']:,.2f}"},
                {"Metric": "Final Portfolio Value", "Value": f"₹{metrics['final_equity']:,.2f}"},
                {"Metric": "Net Total Return", "Value": f"{metrics['net_return_pct']:.2f}%"},
                {"Metric": "CAGR (Annualized)", "Value": f"{metrics['cagr_pct']:.2f}%"},
                {"Metric": "Annualized Volatility", "Value": f"{metrics['annualized_volatility_pct']:.2f}%"},
                {"Metric": "Sharpe Ratio (Rf=6.5%)", "Value": f"{metrics['sharpe_ratio']:.2f}"},
                {"Metric": "Sortino Ratio", "Value": f"{metrics['sortino_ratio']:.2f}"},
                {"Metric": "Calmar Ratio", "Value": f"{metrics['calmar_ratio']:.2f}"},
                {"Metric": "Max Drawdown", "Value": f"{metrics['max_drawdown_pct']:.2f}%"},
                {"Metric": "Max Drawdown Duration", "Value": f"{metrics['max_drawdown_duration_bars']} bars"},
            ]).set_index("Metric"))
            
        with tearsheet_cols[1]:
            st.markdown("#### Execution & Trade Efficiency")
            st.table(pd.DataFrame([
                {"Metric": "Total Closed Trades", "Value": str(metrics["total_closed_trades"])},
                {"Metric": "Win Rate", "Value": f"{metrics['win_rate_pct']:.2f}%"},
                {"Metric": "Winning Trades", "Value": str(metrics["winning_trades"])},
                {"Metric": "Losing Trades", "Value": str(metrics["losing_trades"])},
                {"Metric": "Profit Factor", "Value": f"{metrics['profit_factor']:.2f}"},
                {"Metric": "Average Win", "Value": f"₹{metrics['avg_win_inr']:,.2f}"},
                {"Metric": "Average Loss", "Value": f"₹{metrics['avg_loss_inr']:,.2f}"},
                {"Metric": "Win/Loss Payoff Ratio", "Value": f"{metrics['win_loss_payoff_ratio']:.2f}"},
                {"Metric": "Average Holding Duration", "Value": f"{metrics['avg_holding_bars']:.1f} bars"},
                {"Metric": "Total Friction Paid", "Value": f"₹{metrics['total_friction_inr']:,.2f}"},
            ]).set_index("Metric"))

    with tab_data_audit:
        st.subheader("Dataset Ingestion & Data Quality Audit")
        val_res = validate_market_data(df, source_name=data_option)
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Validated Bars", val_res.metrics.get("clean_rows", 0))
        m_col2.metric("Date Span (Days)", val_res.metrics.get("total_days_span", 0))
        m_col3.metric("Zero-Volume Bars", val_res.metrics.get("zero_volume_bars", 0))
        
        if val_res.warnings:
            st.markdown("##### Data Quality Audit Warnings")
            for w in val_res.warnings:
                st.warning(f"&bull; {w}")
        else:
            st.success("Zero anomalies detected. Data conforms strictly to OHLCV geometric standards.")
            
        st.markdown("##### Data Source Metadata")
        st.json(val_res.metrics)

    with tab_export:
        st.subheader("Export Research Reports & Experiment Configurations")
        st.markdown("Conforms to SOP Section 12 & 14: Reproducible research archives.")
        
        exp_col1, exp_col2 = st.columns(2)
        
        with exp_col1:
            st.markdown("#### Download Trade Logs & Equity Curves")
            trades_csv = export_trades_csv(result.trades)
            st.download_button(
                "📥 Download Trades Log (CSV)",
                data=trades_csv,
                file_name=f"quantedge_trades_{result.symbol}_{selected_strat_key}.csv",
                mime="text/csv"
            )
            
            equity_csv = export_equity_csv(result.equity_curve)
            st.download_button(
                "📥 Download Daily Equity Curve (CSV)",
                data=equity_csv,
                file_name=f"quantedge_equity_{result.symbol}_{selected_strat_key}.csv",
                mime="text/csv"
            )
            
        with exp_col2:
            st.markdown("#### Download Research Report & Experiment YAML")
            html_tearsheet = generate_html_tear_sheet(result, metrics)
            st.download_button(
                "📄 Download Institutional Tear Sheet (HTML)",
                data=html_tearsheet,
                file_name=f"quantedge_report_{result.symbol}_{selected_strat_key}.html",
                mime="text/html"
            )
            
            config_dump = {
                "strategy": selected_strat_key,
                "parameters": user_params,
                "execution": result.execution_assumptions,
                "dataset": data_option,
                "date_range": [start_filter, end_filter],
                "initial_capital": initial_cap
            }
            yaml_str = export_config_yaml(config_dump)
            st.download_button(
                "⚙️ Download Reproducible Configuration (YAML)",
                data=yaml_str,
                file_name=f"config_{result.symbol}_{selected_strat_key}.yaml",
                mime="text/yaml"
            )

    # Footer
    st.markdown("""
    <div style="margin-top: 3rem; padding: 1.5rem; text-align: center; border-top: 1px solid rgba(255,255,255,0.08); color: #64748B; font-size: 0.82rem;">
        <strong>QuantEdge Algorithmic Trading Systems &bull; SOP-QUANT-001 Compliant</strong><br>
        Historical simulation and paper trading only &bull; Live broker order execution is permanently disabled.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
