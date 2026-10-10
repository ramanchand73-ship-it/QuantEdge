"""Transaction cost and statutory tax modeling for NSE India.

Conforms to SOP-QUANT-001 (Section 8: Transaction Costs & Execution Realism).
Computes exact itemized costs:
- Brokerage (percentage or capped flat fee per order)
- Securities Transaction Tax (STT)
- Exchange Transaction Charges (NSE)
- SEBI Regulatory Turnover Fees
- Stamp Duty (State Stamp Act)
- Goods and Services Tax (GST @ 18% on service components)
- Market Slippage (basis points)
- Bid-Ask Spread adjustment
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


@dataclass
class CostBreakdown:
    """Detailed itemized cost components for an executed trade."""
    turnover: float
    brokerage: float
    stt: float
    exchange_charges: float
    sebi_fees: float
    stamp_duty: float
    gst: float
    slippage_cost: float
    half_spread_cost: float
    total_statutory_and_brokerage: float
    total_friction: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "turnover": round(self.turnover, 2),
            "brokerage": round(self.brokerage, 2),
            "stt": round(self.stt, 2),
            "exchange_charges": round(self.exchange_charges, 2),
            "sebi_fees": round(self.sebi_fees, 2),
            "stamp_duty": round(self.stamp_duty, 2),
            "gst": round(self.gst, 2),
            "slippage_cost": round(self.slippage_cost, 2),
            "half_spread_cost": round(self.half_spread_cost, 2),
            "total_statutory_and_brokerage": round(self.total_statutory_and_brokerage, 2),
            "total_friction": round(self.total_friction, 2),
        }


@dataclass
class CostModel:
    """Configurable cost model representing an exchange and brokerage fee structure."""
    name: str = "nse_equity_delivery"
    description: str = "NSE Cash Equity Delivery"
    brokerage_type: str = "flat_or_percent"     # 'flat_per_order', 'percent', 'flat_or_percent', 'zero'
    brokerage_percent: float = 0.0005          # 0.05%
    brokerage_flat_inr: float = 20.0           # ₹20 cap
    brokerage_min_inr: float = 0.0
    stt_buy_percent: float = 0.001             # 0.1% on Buy
    stt_sell_percent: float = 0.001            # 0.1% on Sell
    exchange_txn_charge_percent: float = 0.0000345 # 0.00345%
    sebi_turnover_fee_percent: float = 0.000001    # ₹10 per crore (0.0001%)
    stamp_duty_buy_percent: float = 0.00015    # 0.015% on Buy only
    stamp_duty_sell_percent: float = 0.0
    gst_percent: float = 0.18                  # 18% GST
    default_slippage_bps: float = 5.0          # 5 bps
    default_half_spread_bps: float = 2.0       # 2 bps
    lot_size: int = 1

    @classmethod
    def from_dict(cls, data: Dict[str, Any], name: str = "custom") -> "CostModel":
        return cls(
            name=name,
            description=data.get("description", "Custom Cost Model"),
            brokerage_type=data.get("brokerage_type", "flat_or_percent"),
            brokerage_percent=float(data.get("brokerage_percent", 0.0005)),
            brokerage_flat_inr=float(data.get("brokerage_flat_inr", 20.0)),
            brokerage_min_inr=float(data.get("brokerage_min_inr", 0.0)),
            stt_buy_percent=float(data.get("stt_buy_percent", 0.001)),
            stt_sell_percent=float(data.get("stt_sell_percent", 0.001)),
            exchange_txn_charge_percent=float(data.get("exchange_txn_charge_percent", 0.0000345)),
            sebi_turnover_fee_percent=float(data.get("sebi_turnover_fee_percent", 0.000001)),
            stamp_duty_buy_percent=float(data.get("stamp_duty_buy_percent", 0.00015)),
            stamp_duty_sell_percent=float(data.get("stamp_duty_sell_percent", 0.0)),
            gst_percent=float(data.get("gst_percent", 0.18)),
            default_slippage_bps=float(data.get("default_slippage_bps", 5.0)),
            default_half_spread_bps=float(data.get("default_half_spread_bps", 2.0)),
            lot_size=int(data.get("lot_size", 1))
        )

    def calculate_trade_costs(
        self,
        action: str,
        execution_price: float,
        shares: int,
        custom_slippage_bps: Optional[float] = None
    ) -> CostBreakdown:
        """Calculates itemized costs for a trade execution.
        
        Parameters:
            action: 'BUY' or 'SELL'.
            execution_price: Raw unadjusted fill price before friction.
            shares: Number of shares.
            custom_slippage_bps: Optional override for slippage.
            
        Returns:
            CostBreakdown object.
        """
        turnover = execution_price * shares
        is_buy = action.upper() == "BUY"
        
        # 1. Brokerage
        if self.brokerage_type == "zero":
            brokerage = 0.0
        elif self.brokerage_type == "flat_per_order":
            brokerage = min(self.brokerage_flat_inr, turnover * self.brokerage_percent)
            brokerage = max(brokerage, self.brokerage_min_inr)
        elif self.brokerage_type == "flat_or_percent":
            brokerage = min(self.brokerage_flat_inr, turnover * self.brokerage_percent)
            brokerage = max(brokerage, self.brokerage_min_inr)
        elif self.brokerage_type == "percent":
            brokerage = turnover * self.brokerage_percent
        else:
            brokerage = min(self.brokerage_flat_inr, turnover * self.brokerage_percent)
            
        # 2. STT (Securities Transaction Tax)
        stt_rate = self.stt_buy_percent if is_buy else self.stt_sell_percent
        stt = round(turnover * stt_rate, 2)
        
        # 3. Exchange Transaction Charges
        exchange_charges = turnover * self.exchange_txn_charge_percent
        
        # 4. SEBI Regulatory Turnover Fees
        sebi_fees = turnover * self.sebi_turnover_fee_percent
        
        # 5. Stamp Duty (State Stamp Act)
        stamp_rate = self.stamp_duty_buy_percent if is_buy else self.stamp_duty_sell_percent
        stamp_duty = turnover * stamp_rate
        
        # 6. GST (18% on Brokerage + Exchange charges + SEBI charges)
        gst_taxable_services = brokerage + exchange_charges + sebi_fees
        gst = gst_taxable_services * self.gst_percent
        
        # Total statutory and brokerage fees (cash deduction)
        total_statutory = brokerage + stt + exchange_charges + sebi_fees + stamp_duty + gst
        
        # 7. Slippage & Spread friction (price impact)
        slippage_bps = custom_slippage_bps if custom_slippage_bps is not None else self.default_slippage_bps
        slippage_cost = turnover * (slippage_bps / 10000.0)
        half_spread_cost = turnover * (self.default_half_spread_bps / 10000.0)
        
        total_friction = total_statutory + slippage_cost + half_spread_cost
        
        return CostBreakdown(
            turnover=turnover,
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            sebi_fees=sebi_fees,
            stamp_duty=stamp_duty,
            gst=gst,
            slippage_cost=slippage_cost,
            half_spread_cost=half_spread_cost,
            total_statutory_and_brokerage=total_statutory,
            total_friction=total_friction
        )

    def compute_effective_fill_price(
        self,
        action: str,
        nominal_price: float,
        custom_slippage_bps: Optional[float] = None
    ) -> float:
        """Applies slippage and half-spread to get the realistic execution price.
        
        For BUY: price shifts UPWARD (buyer pays higher).
        For SELL: price shifts DOWNWARD (seller receives lower).
        """
        slippage_bps = custom_slippage_bps if custom_slippage_bps is not None else self.default_slippage_bps
        total_bps = slippage_bps + self.default_half_spread_bps
        adjustment = total_bps / 10000.0
        
        if action.upper() == "BUY":
            return nominal_price * (1.0 + adjustment)
        else:
            return nominal_price * (1.0 - adjustment)


def load_cost_model(model_name: str = "nse_equity_delivery", config_file: Optional[Path] = None) -> CostModel:
    """Loads a cost model from YAML configuration or falls back to defaults."""
    if config_file is None:
        config_file = Path("config/nse_cost_models.yaml")
        
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            models = cfg.get("models", {})
            if model_name in models:
                return CostModel.from_dict(models[model_name], name=model_name)
                
    # Fallback default
    if model_name == "zero_cost_ideal":
        return CostModel(name="zero_cost_ideal", brokerage_type="zero", brokerage_percent=0.0,
                         stt_buy_percent=0.0, stt_sell_percent=0.0, exchange_txn_charge_percent=0.0,
                         sebi_turnover_fee_percent=0.0, stamp_duty_buy_percent=0.0, gst_percent=0.0,
                         default_slippage_bps=0.0, default_half_spread_bps=0.0)
    return CostModel(name="nse_equity_delivery")
