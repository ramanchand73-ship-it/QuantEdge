"""Unit tests for NSE India transaction cost modeling and slippage math."""

import pytest
import numpy as np

from src.backtesting.costs import CostModel, load_cost_model


def test_nse_equity_delivery_cost_breakdown():
    """Validates itemized statutory taxes and brokerage for NSE Equity Delivery."""
    model = CostModel(
        brokerage_type="flat_or_percent",
        brokerage_percent=0.0005,
        brokerage_flat_inr=20.0,
        stt_buy_percent=0.001,
        stt_sell_percent=0.001,
        exchange_txn_charge_percent=0.0000345,
        sebi_turnover_fee_percent=0.000001,
        stamp_duty_buy_percent=0.00015,
        stamp_duty_sell_percent=0.0,
        gst_percent=0.18,
        default_slippage_bps=5.0,
        default_half_spread_bps=2.0
    )
    
    price = 2000.0
    shares = 100
    turnover = price * shares  # 200,000
    
    breakdown_buy = model.calculate_trade_costs("BUY", price, shares)
    
    # 1. Brokerage capped at flat ₹20
    assert np.isclose(breakdown_buy.brokerage, 20.0)
    # 2. STT (0.1% on Buy) = 200.0
    assert np.isclose(breakdown_buy.stt, 200.0)
    # 3. Exchange charge (0.00345%) = 6.90
    assert np.isclose(breakdown_buy.exchange_charges, 6.90)
    # 4. SEBI fee = 0.20
    assert np.isclose(breakdown_buy.sebi_fees, 0.20)
    # 5. Stamp duty on Buy (0.015%) = 30.0
    assert np.isclose(breakdown_buy.stamp_duty, 30.0)
    # 6. GST (18% on Brokerage 20 + Exch 6.9 + SEBI 0.2 = 27.1) = 4.878
    expected_gst = (20.0 + 6.90 + 0.20) * 0.18
    assert np.isclose(breakdown_buy.gst, expected_gst)
    
    # Check total statutory
    assert breakdown_buy.total_statutory_and_brokerage > 0
    assert breakdown_buy.total_friction > breakdown_buy.total_statutory_and_brokerage


def test_slippage_and_spread_direction():
    """Buying shifts execution price higher; selling shifts execution price lower."""
    model = CostModel(default_slippage_bps=10.0, default_half_spread_bps=2.0)
    nominal_price = 1000.0
    
    buy_px = model.compute_effective_fill_price("BUY", nominal_price)
    sell_px = model.compute_effective_fill_price("SELL", nominal_price)
    
    # Total friction = 12 bps = 0.12% -> Buy: 1001.20, Sell: 998.80
    assert buy_px > nominal_price
    assert sell_px < nominal_price
    assert np.isclose(buy_px, 1001.20)
    assert np.isclose(sell_px, 998.80)


def test_zero_cost_model():
    """Zero cost ideal model should produce exactly zero friction."""
    model = load_cost_model("zero_cost_ideal")
    costs = model.calculate_trade_costs("BUY", 1500.0, 50)
    assert costs.total_statutory_and_brokerage == 0.0
    assert costs.total_friction == 0.0
    assert model.compute_effective_fill_price("BUY", 1500.0) == 1500.0
