"""Order and Trade models conforming to SOP-QUANT-001 (Section 7 & 9).

Tracks lifecycle of simulated orders, fills, rejections, and round-trip trade accounting.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import pandas as pd

from src.backtesting.costs import CostBreakdown


@dataclass
class Order:
    """Represents an order instruction sent to the simulated execution venue."""
    order_id: str
    symbol: str
    created_time: pd.Timestamp
    action: str                       # 'BUY' or 'SELL'
    shares: int
    order_type: str = "MARKET"
    status: str = "PENDING"           # 'PENDING', 'FILLED', 'REJECTED', 'CANCELLED'
    fill_price: float = 0.0
    fill_time: Optional[pd.Timestamp] = None
    cost_breakdown: Optional[CostBreakdown] = None
    rejection_reason: Optional[str] = None
    tag: str = "signal"


@dataclass
class Trade:
    """Represents a completed round-trip trade."""
    trade_id: int
    symbol: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    shares: int
    direction: str = "LONG"          # 'LONG' or 'SHORT'
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    return_pct: float = 0.0
    total_friction: float = 0.0
    holding_bars: int = 0
    exit_reason: str = "SIGNAL"      # 'SIGNAL', 'STOP_LOSS', 'TAKE_PROFIT', 'END_OF_TEST'
    entry_costs: Optional[CostBreakdown] = None
    exit_costs: Optional[CostBreakdown] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "entry_time": str(self.entry_time),
            "exit_time": str(self.exit_time),
            "entry_price": round(self.entry_price, 2),
            "exit_price": round(self.exit_price, 2),
            "shares": self.shares,
            "direction": self.direction,
            "gross_pnl": round(self.gross_pnl, 2),
            "net_pnl": round(self.net_pnl, 2),
            "return_pct": round(self.return_pct, 4),
            "total_friction": round(self.total_friction, 2),
            "holding_bars": self.holding_bars,
            "exit_reason": self.exit_reason
        }
