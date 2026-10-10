"""Relative Strength Index (RSI) strategy implementation.

Conforms to SOP-QUANT-001 (Section 6: Strategy B).
- Calculates RSI using Wilder's smoothing technique.
- Enter Long when RSI enters/recovers from oversold territory (e.g. < 30 or cross above).
- Exit position when RSI enters overbought territory (e.g. >= 70).
- Undefined initial warmup periods strictly output 0 (Cash/Neutral).
- Parameter validation strictly prevents invalid thresholds.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np

from src.strategies.base import BaseStrategy


def calculate_wilder_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """Computes RSI using J. Welles Wilder's smoothed moving average.
    
    Strictly causal with zero future data leakage.
    
    Parameters:
        close_series: Series of close prices.
        period: RSI lookback window.
        
    Returns:
        pd.Series of RSI values between 0.0 and 100.0.
    """
    delta = close_series.diff()
    
    # Separate gains and losses
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    
    # Wilder's exponential smoothing (alpha = 1 / period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    
    # Relative strength (RS)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Handle edge case where avg_loss is 0 (100% gains)
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    # Handle edge case where avg_gain is 0 (100% losses)
    rsi = rsi.where(avg_gain != 0.0, 0.0)
    
    return rsi


class RSIStrategy(BaseStrategy):
    """RSI Momentum / Mean-Reversion Strategy."""
    
    name: str = "rsi_strategy"
    display_name: str = "Relative Strength Index (RSI) Oscillator"
    description: str = "Buys oversold pullbacks (RSI <= oversold threshold) and exits when momentum reaches overbought levels (RSI >= overbought threshold)."
    
    @classmethod
    def default_parameters(cls) -> Dict[str, Any]:
        return {
            "rsi_period": 14,
            "oversold_threshold": 30.0,
            "overbought_threshold": 70.0,
            "exit_on_neutral": False,
            "trade_direction": "long_only"
        }
        
    @classmethod
    def parameter_schema(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "rsi_period": {
                "type": "int",
                "default": 14,
                "min": 2,
                "max": 100,
                "step": 1,
                "description": "Lookback period for the RSI calculation."
            },
            "oversold_threshold": {
                "type": "float",
                "default": 30.0,
                "min": 5.0,
                "max": 49.0,
                "step": 1.0,
                "description": "RSI level below which the asset is considered oversold (entry threshold)."
            },
            "overbought_threshold": {
                "type": "float",
                "default": 70.0,
                "min": 51.0,
                "max": 95.0,
                "step": 1.0,
                "description": "RSI level above which the asset is considered overbought (exit threshold)."
            },
            "exit_on_neutral": {
                "type": "bool",
                "default": False,
                "description": "If enabled, exits position when RSI crosses midline 50.0."
            },
            "trade_direction": {
                "type": "choice",
                "default": "long_only",
                "options": ["long_only", "long_short"],
                "description": "Permitted trading direction."
            }
        }
        
    def validate_parameters(self) -> None:
        period = self.params.get("rsi_period")
        oversold = self.params.get("oversold_threshold")
        overbought = self.params.get("overbought_threshold")
        direction = self.params.get("trade_direction")
        
        if not isinstance(period, int) or period < 2:
            raise ValueError(f"rsi_period must be an integer >= 2, got {period}")
        if not isinstance(oversold, (int, float)) or not (0.0 < oversold < 100.0):
            raise ValueError(f"oversold_threshold must be between 0.0 and 100.0, got {oversold}")
        if not isinstance(overbought, (int, float)) or not (0.0 < overbought < 100.0):
            raise ValueError(f"overbought_threshold must be between 0.0 and 100.0, got {overbought}")
        if oversold >= overbought:
            raise ValueError(f"oversold_threshold ({oversold}) must be strictly less than overbought_threshold ({overbought})")
        if direction not in ("long_only", "long_short"):
            raise ValueError(f"Invalid trade_direction: {direction}. Must be 'long_only' or 'long_short'")
            
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculates RSI indicator on 'close' series."""
        df = data.copy()
        period = self.params["rsi_period"]
        df["rsi"] = calculate_wilder_rsi(df["close"], period=period)
        return df
        
    def generate_signals(self, data_with_indicators: pd.DataFrame) -> pd.Series:
        """Generates position signals based on RSI thresholds.
        
        State machine simulation:
        - When in cash (0):
            - If RSI <= oversold_threshold: Switch to Long (1)
            - If RSI >= overbought_threshold and long_short: Switch to Short (-1)
        - When in Long (1):
            - If RSI >= overbought_threshold: Switch to Cash (0)
            - If exit_on_neutral and RSI >= 50.0: Switch to Cash (0)
        - When in Short (-1):
            - If RSI <= oversold_threshold: Switch to Cash (0)
            - If exit_on_neutral and RSI <= 50.0: Switch to Cash (0)
        """
        df = data_with_indicators
        rsi = df["rsi"].values
        n = len(df)
        
        oversold = float(self.params["oversold_threshold"])
        overbought = float(self.params["overbought_threshold"])
        exit_neutral = bool(self.params.get("exit_on_neutral", False))
        direction = str(self.params.get("trade_direction", "long_only"))
        
        signals = np.zeros(n, dtype=int)
        current_pos = 0
        
        for i in range(n):
            current_rsi = rsi[i]
            
            # During warmup or NaN, keep position flat
            if np.isnan(current_rsi):
                current_pos = 0
                signals[i] = 0
                continue
                
            if current_pos == 0:
                if current_rsi <= oversold:
                    current_pos = 1
                elif direction == "long_short" and current_rsi >= overbought:
                    current_pos = -1
            elif current_pos == 1:
                # Long exit criteria
                if current_rsi >= overbought or (exit_neutral and current_rsi >= 50.0):
                    current_pos = 0
            elif current_pos == -1:
                # Short exit criteria
                if current_rsi <= oversold or (exit_neutral and current_rsi <= 50.0):
                    current_pos = 0
                    
            signals[i] = current_pos
            
        return pd.Series(signals, index=df.index, dtype=int)
