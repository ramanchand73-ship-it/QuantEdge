"""Deterministic historical backtesting engine conforming to SOP-QUANT-001.

Simulates trade execution bar-by-bar with documented execution semantics:
- Signal computed at Bar T Close -> Executed at Bar T+1 Open.
- Strict no-look-ahead causality.
- Real-world NSE transaction cost deductions and slippage modeling.
- Conservative intrabar stop-loss and take-profit execution.
- Benchmark comparison and audit-ready execution logs.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union
import numpy as np
import pandas as pd

from src.strategies.base import BaseStrategy
from src.backtesting.costs import CostModel, load_cost_model
from src.backtesting.portfolio import Portfolio
from src.backtesting.order import Order


@dataclass
class BacktestResult:
    """Encapsulates complete simulation outputs."""
    strategy_name: str
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_equity: float
    total_net_pnl: float
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    orders: list
    rejected_orders: list
    cost_summary: Dict[str, float]
    strategy_params: Dict[str, Any]
    execution_assumptions: Dict[str, Any]
    benchmark_equity: Optional[pd.Series] = None
    data_with_signals: Optional[pd.DataFrame] = None


class BacktestEngine:
    """Core event-driven / bar-by-bar backtesting engine."""

    def __init__(
        self,
        strategy: BaseStrategy,
        cost_model: Optional[CostModel] = None,
        initial_capital: float = 1_000_000.0,
        allocation_pct: float = 0.95,
        signal_delay_bars: int = 1,
        slippage_bps: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        close_positions_at_end: bool = True
    ):
        """Initializes the backtesting engine.
        
        Parameters:
            strategy: Concrete BaseStrategy instance.
            cost_model: CostModel instance (defaults to NSE equity delivery).
            initial_capital: Virtual starting cash (INR).
            allocation_pct: Target capital fraction allocated to trade (0.0 < x <= 1.0).
            signal_delay_bars: Execution latency (1 means Signal at T close -> Fill at T+1 open).
            slippage_bps: Slippage override in basis points.
            stop_loss_pct: Optional stop-loss fraction (e.g., 0.05 for 5%).
            take_profit_pct: Optional take-profit fraction (e.g., 0.10 for 10%).
            close_positions_at_end: If True, liquidates open position on final bar.
        """
        self.strategy = strategy
        self.cost_model = cost_model or load_cost_model("nse_equity_delivery")
        self.initial_capital = float(initial_capital)
        self.allocation_pct = min(1.0, max(0.01, float(allocation_pct)))
        self.signal_delay_bars = int(signal_delay_bars)
        self.slippage_bps = slippage_bps
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.close_positions_at_end = close_positions_at_end

    def run(
        self,
        data: pd.DataFrame,
        benchmark_data: Optional[pd.DataFrame] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> BacktestResult:
        """Executes historical simulation over the provided market dataset.
        
        Parameters:
            data: Validated DataFrame with DatetimeIndex and ['open', 'high', 'low', 'close', 'volume'].
            benchmark_data: Optional market DataFrame for benchmark comparison (e.g. NIFTY 50).
            start_date: Optional filter start date (YYYY-MM-DD).
            end_date: Optional filter end date (YYYY-MM-DD).
            
        Returns:
            BacktestResult with equity curve, trades, metrics, and logs.
        """
        if data is None or len(data) == 0:
            raise ValueError("Input market dataset is empty.")
            
        df = data.copy()
        if not df.index.is_monotonic_increasing:
            df = df.sort_index()
            
        # Date range filtering
        if start_date:
            df = df.loc[df.index >= pd.to_datetime(start_date)]
        if end_date:
            df = df.loc[df.index <= pd.to_datetime(end_date)]
            
        if len(df) < 5:
            raise ValueError(f"Insufficient historical bars ({len(df)}) in selected date range.")
            
        symbol = str(df["symbol"].iloc[0]) if "symbol" in df.columns else "EQUITY"
        
        # 1. Compute strategy indicators and signals causal-by-causal
        prepared_df = self.strategy.run_signal_generation(df)
        signals = prepared_df["signal"].values
        opens = prepared_df["open"].values
        highs = prepared_df["high"].values
        lows = prepared_df["low"].values
        closes = prepared_df["close"].values
        dates = prepared_df.index
        n_bars = len(prepared_df)
        
        # 2. Initialize portfolio
        portfolio = Portfolio(initial_capital=self.initial_capital, symbol=symbol)
        order_seq = 0
        
        # 3. Bar-by-bar execution loop
        for t in range(n_bars):
            bar_date = dates[t]
            bar_open = opens[t]
            bar_high = highs[t]
            bar_low = lows[t]
            bar_close = closes[t]
            
            # --- Check Intrabar Risk Controls on Existing Positions First ---
            if portfolio.shares > 0 and (self.stop_loss_pct or self.take_profit_pct):
                entry_px = portfolio.avg_entry_price
                sl_price = entry_px * (1.0 - self.stop_loss_pct) if self.stop_loss_pct else -np.inf
                tp_price = entry_px * (1.0 + self.take_profit_pct) if self.take_profit_pct else np.inf
                
                sl_hit = bar_low <= sl_price
                tp_hit = bar_high >= tp_price
                
                # If both hit in the same bar, assume conservative Stop Loss
                if sl_hit:
                    fill_nominal = min(bar_open, sl_price)
                    fill_effective = self.cost_model.compute_effective_fill_price("SELL", fill_nominal, self.slippage_bps)
                    costs = self.cost_model.calculate_trade_costs("SELL", fill_effective, portfolio.shares, self.slippage_bps)
                    order_seq += 1
                    sl_order = Order(
                        order_id=f"ORD-SL-{order_seq:05d}",
                        symbol=symbol,
                        created_time=bar_date,
                        action="SELL",
                        shares=portfolio.shares,
                        tag="stop_loss"
                    )
                    portfolio.execute_sell(sl_order, fill_effective, costs, bar_idx=t, exit_reason="STOP_LOSS")
                elif tp_hit:
                    fill_nominal = max(bar_open, tp_price)
                    fill_effective = self.cost_model.compute_effective_fill_price("SELL", fill_nominal, self.slippage_bps)
                    costs = self.cost_model.calculate_trade_costs("SELL", fill_effective, portfolio.shares, self.slippage_bps)
                    order_seq += 1
                    tp_order = Order(
                        order_id=f"ORD-TP-{order_seq:05d}",
                        symbol=symbol,
                        created_time=bar_date,
                        action="SELL",
                        shares=portfolio.shares,
                        tag="take_profit"
                    )
                    portfolio.execute_sell(tp_order, fill_effective, costs, bar_idx=t, exit_reason="TAKE_PROFIT")
                    
            # --- Execute Pending Signal-Based Orders at Bar Open ---
            # Signal was generated at bar t-1 close. Executes at bar t Open.
            if t >= self.signal_delay_bars:
                decision_idx = t - self.signal_delay_bars
                prior_signal = signals[decision_idx]
                
                # If signal calls for LONG (1) and currently flat
                if prior_signal == 1 and portfolio.shares == 0:
                    nominal_px = bar_open
                    effective_px = self.cost_model.compute_effective_fill_price("BUY", nominal_px, self.slippage_bps)
                    
                    # Position sizing calculation
                    target_capital = portfolio.cash * self.allocation_pct
                    # Reserve 1% for transaction costs to avoid rejection
                    usable_capital = target_capital * 0.99
                    target_shares = int(usable_capital // effective_px)
                    
                    if target_shares >= self.cost_model.lot_size:
                        costs = self.cost_model.calculate_trade_costs("BUY", effective_px, target_shares, self.slippage_bps)
                        order_seq += 1
                        buy_order = Order(
                            order_id=f"ORD-{order_seq:05d}",
                            symbol=symbol,
                            created_time=bar_date,
                            action="BUY",
                            shares=target_shares,
                            tag="signal_entry"
                        )
                        portfolio.execute_buy(buy_order, effective_px, costs, bar_idx=t)
                        
                # If signal calls for EXIT/CASH (0) and currently long
                elif prior_signal == 0 and portfolio.shares > 0:
                    nominal_px = bar_open
                    effective_px = self.cost_model.compute_effective_fill_price("SELL", nominal_px, self.slippage_bps)
                    costs = self.cost_model.calculate_trade_costs("SELL", effective_px, portfolio.shares, self.slippage_bps)
                    order_seq += 1
                    sell_order = Order(
                        order_id=f"ORD-{order_seq:05d}",
                        symbol=symbol,
                        created_time=bar_date,
                        action="SELL",
                        shares=portfolio.shares,
                        tag="signal_exit"
                    )
                    portfolio.execute_sell(sell_order, effective_px, costs, bar_idx=t, exit_reason="SIGNAL")
                    
            # End of bar: Mark portfolio to market at Bar Close
            portfolio.mark_to_market(bar_date, bar_close, bar_idx=t)
            
        # 4. Optional end-of-test position liquidation at final bar close
        if self.close_positions_at_end and portfolio.shares > 0:
            final_date = dates[-1]
            final_close = closes[-1]
            effective_px = self.cost_model.compute_effective_fill_price("SELL", final_close, self.slippage_bps)
            costs = self.cost_model.calculate_trade_costs("SELL", effective_px, portfolio.shares, self.slippage_bps)
            order_seq += 1
            close_order = Order(
                order_id=f"ORD-CLOSE-{order_seq:05d}",
                symbol=symbol,
                created_time=final_date,
                action="SELL",
                shares=portfolio.shares,
                tag="end_of_test"
            )
            portfolio.execute_sell(close_order, effective_px, costs, bar_idx=n_bars-1, exit_reason="END_OF_TEST")
            portfolio.history[-1] = portfolio.mark_to_market(final_date, final_close, bar_idx=n_bars-1)
            
        equity_df = portfolio.get_equity_curve_df()
        trades_df = portfolio.get_trades_df()
        
        # 5. Benchmark calculation
        benchmark_series = None
        if benchmark_data is not None and not benchmark_data.empty:
            b_df = benchmark_data.loc[(benchmark_data.index >= equity_df.index.min()) & (benchmark_data.index <= equity_df.index.max())]
            if not b_df.empty and "close" in b_df.columns:
                b_reindexed = b_df["close"].reindex(equity_df.index, method="ffill")
                if not b_reindexed.empty and b_reindexed.iloc[0] > 0:
                    benchmark_series = (b_reindexed / b_reindexed.iloc[0]) * self.initial_capital
                    
        if benchmark_series is None and "close" in df.columns:
            # Default benchmark: Buy & Hold underlying
            underlying_closes = df["close"].loc[equity_df.index]
            benchmark_series = (underlying_closes / underlying_closes.iloc[0]) * self.initial_capital
            
        cost_sum = {
            "total_friction": round(portfolio.cumulative_friction, 2),
            "trade_count": len(portfolio.completed_trades),
            "rejected_orders_count": len(portfolio.rejected_orders)
        }
        
        final_eq = equity_df["equity"].iloc[-1] if not equity_df.empty else self.initial_capital
        
        return BacktestResult(
            strategy_name=self.strategy.name,
            symbol=symbol,
            start_date=str(equity_df.index.min()),
            end_date=str(equity_df.index.max()),
            initial_capital=self.initial_capital,
            final_equity=round(final_eq, 2),
            total_net_pnl=round(final_eq - self.initial_capital, 2),
            equity_curve=equity_df,
            trades=trades_df,
            orders=portfolio.all_orders,
            rejected_orders=portfolio.rejected_orders,
            cost_summary=cost_sum,
            strategy_params=self.strategy.params,
            execution_assumptions={
                "cost_model": self.cost_model.name,
                "signal_delay_bars": self.signal_delay_bars,
                "allocation_pct": self.allocation_pct,
                "slippage_bps": self.slippage_bps if self.slippage_bps is not None else self.cost_model.default_slippage_bps,
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct
            },
            benchmark_equity=benchmark_series,
            data_with_signals=prepared_df
        )
