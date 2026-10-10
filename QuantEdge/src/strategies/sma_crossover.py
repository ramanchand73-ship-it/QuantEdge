"""Simple Moving Average (SMA) Crossover strategy implementation.

Conforms to SOP-QUANT-001 (Section 6: Strategy A).
- Computes Fast and Slow rolling Simple Moving Averages.
- Signal = 1 (Long) when Fast SMA > Slow SMA.
- Signal = 0 (Cash / Exit) when Fast SMA <= Slow SMA.
- Strictly guards against undefined warmup bars and look-ahead bias.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from src.strategies.base import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    """Simple Moving Average (SMA) Crossover Strategy."""
    
    name: str = "sma_crossover"
    display_name: str = "SMA Crossover Trend Strategy"
    description: str = "Enters long when fast moving average crosses above slow average; exits when fast crosses below slow."
    
    @classmethod
    def default_parameters(cls) -> Dict[str, Any]:
        return {
            "fast_period": 20,
            "slow_period": 50,
            "trade_direction": "long_only"
        }
        
    @classmethod
    def parameter_schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "fast_period": {
                "type": "int",
                "default": 20,
                "min": 2,
                "max": 200,
                "step": 1,
                "description": "Lookback window for the fast moving average."
            },
            "slow_period": {
                "type": "int",
                "default": 50,
                "min": 5,
                "max": 500,
                "step": 1,
                "description": "Lookback window for the slow moving average (must exceed fast_period)."
            },
            "trade_direction": {
                "type": "choice",
                "default": "long_only",
                "options": ["long_only", "long_short"],
                "description": "Permitted trading direction."
            }
        }
        
    def validate_parameters(self) -> None:
        fast = self.params.get("fast_period")
        slow = self.params.get("slow_period")
        direction = self.params.get("trade_direction")
        
        if not isinstance(fast, int) or fast <= 0:
            raise ValueError(f"fast_period must be a positive integer, got {fast}")
        if not isinstance(slow, int) or slow <= 0:
            raise ValueError(f"slow_period must be a positive integer, got {slow}")
        if fast >= slow:
            raise ValueError(f"fast_period ({fast}) must be strictly less than slow_period ({slow})")
        if direction not in ("long_only", "long_short"):
            raise ValueError(f"Invalid trade_direction: {direction}. Must be 'long_only' or 'long_short'")
            
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculates fast and slow moving averages on the 'close' price.
        
        Strictly causal: uses rolling(window=...).mean().
        """
        df = data.copy()
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        
        df["sma_fast"] = df["close"].rolling(window=fast, min_periods=fast).mean()
        df["sma_slow"] = df["close"].rolling(window=slow, min_periods=slow).mean()
        return df
        
    def generate_signals(self, data_with_indicators: pd.DataFrame) -> pd.Series:
        """Generates trading signals based on SMA relationships.
        
        During warmup (before slow_period is reached), signal is strictly 0 (Cash).
        When sma_fast > sma_slow:
            Long signal = 1
        When sma_fast < sma_slow:
            If long_only: signal = 0 (Cash / Exit)
            If long_short: signal = -1 (Short)
        """
        df = data_with_indicators
        fast_sma = df["sma_fast"]
        slow_sma = df["sma_slow"]
        direction = self.params["trade_direction"]
        
        signals = pd.Series(0, index=df.index, dtype=int)
        
        # Valid mask: both SMAs must be defined (not NaN)
        valid_mask = fast_sma.notna() & slow_sma.notna()
        
        if direction == "long_only":
            long_condition = valid_mask & (fast_sma > slow_sma)
            signals[long_condition] = 1
        else: # long_short
            long_condition = valid_mask & (fast_sma > slow_sma)
            short_condition = valid_mask & (fast_sma < slow_sma)
            signals[long_condition] = 1
            signals[short_condition] = -1
            
        return signals
