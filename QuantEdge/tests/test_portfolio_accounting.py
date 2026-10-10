"""Unit tests for Portfolio Accounting and Cash Management."""

import pytest
import pandas as pd
import numpy as np

from src.backtesting.portfolio import Portfolio
from src.backtesting.order import Order
from src.backtesting.costs import CostBreakdown


def dummy_cost(turnover: float, statutory: float = 50.0, friction: float = 75.0) -> CostBreakdown:
    return CostBreakdown(
        turnover=turnover,
        brokerage=20.0,
        stt=20.0,
        exchange_charges=5.0,
        sebi_fees=0.2,
        stamp_duty=2.0,
        gst=2.8,
        slippage_cost=15.0,
        half_spread_cost=10.0,
        total_statutory_and_brokerage=statutory,
        total_friction=friction
    )


def test_portfolio_cash_accounting():
    """Buying shares reduces cash by (turnover + costs); selling restores proceeds."""
    initial_cash = 100_000.0
    p = Portfolio(initial_capital=initial_cash, symbol="TCS.NS")
    
    price = 1000.0
    shares = 50
    turnover = price * shares  # 50,000
    statutory_cost = 60.0
    
    costs = dummy_cost(turnover, statutory=statutory_cost, friction=100.0)
    order = Order(
        order_id="ORD-01",
        symbol="TCS.NS",
        created_time=pd.Timestamp("2024-01-01"),
        action="BUY",
        shares=shares
    )
    
    success = p.execute_buy(order, price, costs, bar_idx=0)
    assert success is True
    assert p.shares == 50
    expected_cash = initial_cash - (turnover + statutory_cost)
    assert np.isclose(p.cash, expected_cash)
    
    # Sell position at 1100 (Profit of 100/share = 5,000 gross)
    sell_price = 1100.0
    sell_turnover = sell_price * shares  # 55,000
    sell_costs = dummy_cost(sell_turnover, statutory=65.0, friction=110.0)
    sell_order = Order(
        order_id="ORD-02",
        symbol="TCS.NS",
        created_time=pd.Timestamp("2024-01-10"),
        action="SELL",
        shares=shares
    )
    
    sell_success = p.execute_sell(sell_order, sell_price, sell_costs, bar_idx=5)
    assert sell_success is True
    assert p.shares == 0
    assert len(p.completed_trades) == 1
    
    trade = p.completed_trades[0]
    assert np.isclose(trade.gross_pnl, 5000.0)
    assert trade.net_pnl < trade.gross_pnl  # Reduced by frictions
    assert trade.net_pnl > 0


def test_insufficient_cash_rejection():
    """Orders requiring more cash than available balance must be rejected."""
    p = Portfolio(initial_capital=10_000.0, symbol="TCS.NS")
    costs = dummy_cost(50_000.0, statutory=50.0)
    order = Order(
        order_id="ORD-BIG",
        symbol="TCS.NS",
        created_time=pd.Timestamp("2024-01-01"),
        action="BUY",
        shares=50
    )
    
    success = p.execute_buy(order, 1000.0, costs, bar_idx=0)
    assert success is False
    assert order.status == "REJECTED"
    assert "Insufficient cash" in order.rejection_reason
    assert p.cash == 10_000.0
    assert p.shares == 0
    assert len(p.rejected_orders) == 1
