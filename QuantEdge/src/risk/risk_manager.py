"""Risk controls and portfolio guardrails conforming to SOP-QUANT-001 (Section 9)."""

from typing import Dict, Any, Optional


class RiskManager:
    """Evaluates portfolio allocation boundaries, exposure limits, and circuit breakers."""

    def __init__(
        self,
        max_position_pct: float = 1.0,
        max_drawdown_limit: float = 0.25,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None
    ):
        self.max_position_pct = max(0.01, min(1.0, max_position_pct))
        self.max_drawdown_limit = max(0.01, min(1.0, max_drawdown_limit))
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    def check_drawdown_limit(self, current_drawdown: float) -> bool:
        """Returns True if portfolio drawdown exceeds maximum risk tolerance limit."""
        return current_drawdown >= self.max_drawdown_limit

    def calculate_max_shares(self, capital: float, price: float) -> int:
        """Computes permissible shares considering max position size limit."""
        if price <= 0:
            return 0
        max_allocation = capital * self.max_position_pct
        return int(max_allocation // price)
