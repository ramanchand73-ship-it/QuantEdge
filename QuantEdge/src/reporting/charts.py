"""Plotly financial charts for quantitative research and dashboard visualization.

Conforms to SOP-QUANT-001 (Section 12: Dashboard Requirements).
Generates interactive, institutional-grade charts:
- Equity Curve vs. Benchmark
- Underwater Drawdown Chart
- Price Candlestick with Buy/Sell Execution Markers and Indicator Overlays
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_equity_curve_chart(
    equity_df: pd.DataFrame,
    benchmark_series: Optional[pd.Series] = None,
    title: str = "Portfolio Equity vs. Benchmark"
) -> go.Figure:
    """Creates interactive Plotly line chart comparing Strategy equity to Benchmark."""
    fig = go.Figure()
    
    if equity_df is not None and not equity_df.empty:
        fig.add_trace(go.Scatter(
            x=equity_df.index,
            y=equity_df["equity"],
            mode="lines",
            name="Strategy Equity",
            line=dict(color="#00D26A", width=2.5),
            hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>Strategy:</b> ₹%{y:,.2f}<extra></extra>"
        ))
        
        # High-water mark
        if "peak_equity" in equity_df.columns:
            fig.add_trace(go.Scatter(
                x=equity_df.index,
                y=equity_df["peak_equity"],
                mode="lines",
                name="Peak High-Water Mark",
                line=dict(color="rgba(255, 255, 255, 0.25)", width=1.2, dash="dash"),
                hovertemplate="<b>Peak:</b> ₹%{y:,.2f}<extra></extra>"
            ))
            
    if benchmark_series is not None and not benchmark_series.empty:
        fig.add_trace(go.Scatter(
            x=benchmark_series.index,
            y=benchmark_series.values,
            mode="lines",
            name="Benchmark Index (Buy & Hold)",
            line=dict(color="#3B82F6", width=1.8, dash="dot"),
            hovertemplate="<b>Benchmark:</b> ₹%{y:,.2f}<extra></extra>"
        ))
        
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#F8FAFC")),
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#1E293B",
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickformat="%b %Y"
        ),
        yaxis=dict(
            title="Portfolio Value (INR)",
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickprefix="₹"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig


def create_drawdown_chart(
    equity_df: pd.DataFrame,
    title: str = "Underwater Portfolio Drawdown"
) -> go.Figure:
    """Creates Plotly area chart displaying historical peak-to-trough drawdowns."""
    fig = go.Figure()
    
    if equity_df is not None and not equity_df.empty and "drawdown" in equity_df.columns:
        dd_percent = -100.0 * equity_df["drawdown"]
        
        fig.add_trace(go.Scatter(
            x=equity_df.index,
            y=dd_percent,
            mode="lines",
            name="Drawdown",
            line=dict(color="#EF4444", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.25)",
            hovertemplate="<b>Date:</b> %{x|%Y-%m-%d}<br><b>Drawdown:</b> %{y:.2f}%<extra></extra>"
        ))
        
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#F8FAFC")),
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#1E293B",
        xaxis=dict(
            title="Date",
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.15)",
            tickformat="%b %Y"
        ),
        yaxis=dict(
            title="Drawdown (%)",
            showgrid=True,
            gridcolor="rgba(148, 163, 184, 0.15)",
            ticksuffix="%"
        ),
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig


def create_candlestick_trade_chart(
    data: pd.DataFrame,
    trades_df: Optional[pd.DataFrame] = None,
    indicators: Optional[List[str]] = None,
    title: str = "Price Action & Trade Executions"
) -> go.Figure:
    """Creates Candlestick chart overlaid with indicators and buy/sell trade markers."""
    if data is None or data.empty:
        return go.Figure()
        
    # Subplots if RSI is present in indicators
    has_rsi = "rsi" in data.columns and (indicators is None or "rsi" in indicators)
    
    if has_rsi:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.75, 0.25]
        )
    else:
        fig = make_subplots(rows=1, cols=1)
        
    # 1. Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data["open"],
        high=data["high"],
        low=data["low"],
        close=data["close"],
        name="Price OHLC",
        increasing_line_color="#10B981",
        decreasing_line_color="#EF4444"
    ), row=1, col=1)
    
    # 2. Indicator overlays
    if "sma_fast" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["sma_fast"],
            mode="lines",
            name="Fast SMA",
            line=dict(color="#F59E0B", width=1.5)
        ), row=1, col=1)
        
    if "sma_slow" in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["sma_slow"],
            mode="lines",
            name="Slow SMA",
            line=dict(color="#8B5CF6", width=1.5)
        ), row=1, col=1)
        
    # 3. Trade Entry / Exit Markers
    if trades_df is not None and not trades_df.empty:
        buy_times = pd.to_datetime(trades_df["entry_time"])
        buy_prices = trades_df["entry_price"]
        
        sell_times = pd.to_datetime(trades_df["exit_time"])
        sell_prices = trades_df["exit_price"]
        
        # Green Up Triangles for Buy
        fig.add_trace(go.Scatter(
            x=buy_times,
            y=buy_prices,
            mode="markers",
            name="BUY Entry",
            marker=dict(
                symbol="triangle-up",
                size=12,
                color="#22C55E",
                line=dict(width=1, color="#FFFFFF")
            ),
            hovertemplate="<b>BUY</b><br>Date: %{x|%Y-%m-%d}<br>Price: ₹%{y:.2f}<extra></extra>"
        ), row=1, col=1)
        
        # Red Down Triangles for Sell
        fig.add_trace(go.Scatter(
            x=sell_times,
            y=sell_prices,
            mode="markers",
            name="SELL Exit",
            marker=dict(
                symbol="triangle-down",
                size=12,
                color="#EF4444",
                line=dict(width=1, color="#FFFFFF")
            ),
            hovertemplate="<b>SELL</b><br>Date: %{x|%Y-%m-%d}<br>Price: ₹%{y:.2f}<extra></extra>"
        ), row=1, col=1)
        
    # 4. RSI Subplot if applicable
    if has_rsi:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data["rsi"],
            mode="lines",
            name="RSI (14)",
            line=dict(color="#A855F7", width=1.5)
        ), row=2, col=1)
        
        # Overbought line (70)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(239, 68, 68, 0.6)", row=2, col=1)
        # Oversold line (30)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(34, 197, 94, 0.6)", row=2, col=1)
        fig.update_yaxes(title="RSI", range=[0, 100], row=2, col=1)
        
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color="#F8FAFC")),
        template="plotly_dark",
        paper_bgcolor="#0F172A",
        plot_bgcolor="#1E293B",
        xaxis=dict(showgrid=True, gridcolor="rgba(148, 163, 184, 0.15)"),
        yaxis=dict(title="Price (INR)", showgrid=True, gridcolor="rgba(148, 163, 184, 0.15)", tickprefix="₹"),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig
