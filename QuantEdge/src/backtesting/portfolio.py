"""Portfolio accounting and position management module.

Conforms to SOP-QUANT-001 (Section 7: Backtesting Engine & Section 9: Portfolio Management).
Maintains exact mark-to-market valuations, cash ledger, trade records,
and enforces cash constraints (no silent negative cash borrowing).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd

from src.backtesting.order import Order, Trade
from src.backtesting.costs import CostBreakdown


@dataclass
class PortfolioSnapshot:
    """Bar-by-bar portfolio mark-to-market state."""
    timestamp: pd.Timestamp
    cash: float
    shares: int
    close_price: float
    position_value: float
    total_equity: float
    cumulative_friction: float
    drawdown_pct: float
    peak_equity: float


class Portfolio:
    """Deterministic portfolio ledger tracking positions, cash, and risk limits."""

    def __init__(self, initial_capital: float = 1_000_000.0, symbol: str = "TCS.NS"):
        if initial_capital <= 0:
            raise ValueError(f"Initial capital must be positive, got {initial_capital}")
            
        self.initial_capital: float = float(initial_capital)
        self.cash: float = float(initial_capital)
        self.symbol: str = symbol
        
        # Open position state
        self.shares: int = 0
        self.avg_entry_price: float = 0.0
        self.entry_time: Optional[pd.Timestamp] = None
        self.entry_costs: Optional[CostBreakdown] = None
        self.entry_bar_idx: int = 0
        
        # Accounting ledgers
        self.cumulative_friction: float = 0.0
        self.peak_equity: float = float(initial_capital)
        self.completed_trades: List[Trade] = []
        self.all_orders: List[Order] = []
        self.rejected_orders: List[Order] = []
        self.history: List[PortfolioSnapshot] = []
        self._trade_counter: int = 0

    @property
    def total_equity(self) -> float:
        """Current equity based on last known cash and position value."""
        return self.cash + (self.shares * self.avg_entry_price)

    def mark_to_market(self, timestamp: pd.Timestamp, close_price: float, bar_idx: int) -> PortfolioSnapshot:
        """Computes current portfolio valuation at the bar's close price."""
        position_value = self.shares * close_price
        current_equity = self.cash + position_value
        
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            
        dd_pct = (self.peak_equity - current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        
        snapshot = PortfolioSnapshot(
            timestamp=timestamp,
            cash=round(self.cash, 2),
            shares=self.shares,
            close_price=round(close_price, 2),
            position_value=round(position_value, 2),
            total_equity=round(current_equity, 2),
            cumulative_friction=round(self.cumulative_friction, 2),
            drawdown_pct=round(dd_pct, 4),
            peak_equity=round(self.peak_equity, 2)
        )
        self.history.append(snapshot)
        return snapshot

    def execute_buy(
        self,
        order: Order,
        effective_price: float,
        costs: CostBreakdown,
        bar_idx: int
    ) -> bool:
        """Executes a BUY order, deducting total required cash (turnover + costs).
        
        Rejects order if required cash exceeds available cash (zero negative cash allowed).
        """
        required_cash = (effective_price * order.shares) + costs.total_statutory_and_brokerage
        
        if required_cash > self.cash:
            order.status = "REJECTED"
            order.rejection_reason = (
                f"Insufficient cash: Required ₹{required_cash:,.2f} "
                f"(Price ₹{effective_price:.2f} * {order.shares} + Fees ₹{costs.total_statutory_and_brokerage:.2f}) "
                f"exceeds available cash ₹{self.cash:,.2f}"
            )
            self.rejected_orders.append(order)
            self.all_orders.append(order)
            return False
            
        # Deduct cash
        self.cash -= required_cash
        self.shares += order.shares
        self.avg_entry_price = effective_price
        self.entry_time = order.created_time
        self.entry_costs = costs
        self.entry_bar_idx = bar_idx
        self.cumulative_friction += costs.total_friction
        
        order.status = "FILLED"
        order.fill_price = effective_price
        order.cost_breakdown = costs
        self.all_orders.append(order)
        return True

    def execute_sell(
        self,
        order: Order,
        effective_price: float,
        costs: CostBreakdown,
        bar_idx: int,
        exit_reason: str = "SIGNAL"
    ) -> bool:
        """Executes a SELL order (closing existing long position).
        
        Adds net proceeds (turnover - costs) to cash, calculates trade PnL.
        """
        if self.shares <= 0:
            order.status = "REJECTED"
            order.rejection_reason = "No open long position to sell."
            self.rejected_orders.append(order)
            self.all_orders.append(order)
            return False
            
        sell_shares = min(order.shares, self.shares)
        gross_turnover = effective_price * sell_shares
        net_cash_received = gross_turnover - costs.total_statutory_and_brokerage
        
        self.cash += net_cash_received
        self.cumulative_friction += costs.total_friction
        
        # Round-trip trade accounting
        self._trade_counter += 1
        entry_cost_share = self.entry_costs.total_friction if self.entry_costs else 0.0
        total_trade_friction = entry_cost_share + costs.total_friction
        
        gross_pnl = (effective_price - self.avg_entry_price) * sell_shares
        net_pnl = gross_pnl - total_trade_friction
        
        initial_invested = self.avg_entry_price * sell_shares
        return_pct = (net_pnl / initial_invested) if initial_invested > 0 else 0.0
        holding_bars = max(0, bar_idx - self.entry_bar_idx)
        
        trade = Trade(
            trade_id=self._trade_counter,
            symbol=self.symbol,
            entry_time=self.entry_time or order.created_time,
            exit_time=order.created_time,
            entry_price=self.avg_entry_price,
            exit_price=effective_price,
            shares=sell_shares,
            direction="LONG",
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            return_pct=return_pct,
            total_friction=total_trade_friction,
            holding_bars=holding_bars,
            exit_reason=exit_reason,
            entry_costs=self.entry_costs,
            exit_costs=costs
        )
        self.completed_trades.append(trade)
        
        # Reset position
        self.shares -= sell_shares
        if self.shares == 0:
            self.avg_entry_price = 0.0
            self.entry_time = None
            self.entry_costs = None
            self.entry_bar_idx = 0
            
        order.status = "FILLED"
        order.fill_price = effective_price
        order.cost_breakdown = costs
        self.all_orders.append(order)
        return True

    def get_equity_curve_df(self) -> pd.DataFrame:
        """Returns DataFrame of bar-by-bar portfolio equity and drawdowns."""
        if not self.history:
            return pd.DataFrame()
            
        records = [
            {
                "date": snap.timestamp,
                "cash": snap.cash,
                "shares": snap.shares,
                "close": snap.close_price,
                "position_value": snap.position_value,
                "equity": snap.total_equity,
                "drawdown": snap.drawdown_pct,
                "peak_equity": snap.peak_equity,
                "cumulative_friction": snap.cumulative_friction
            }
            for snap in self.history
        ]
        df = pd.DataFrame(records).set_index("date")
        return df

    def get_trades_df(self) -> pd.DataFrame:
        """Returns DataFrame of all completed round-trip trades."""
        if not self.completed_trades:
            return pd.DataFrame(columns=[
                "trade_id", "symbol", "entry_time", "exit_time", "entry_price",
                "exit_price", "shares", "direction", "gross_pnl", "net_pnl",
                "return_pct", "total_friction", "holding_bars", "exit_reason"
            ])
        return pd.DataFrame([t.to_dict() for t in self.completed_trades])
