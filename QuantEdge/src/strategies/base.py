"""Base strategy interface conforming to SOP-QUANT-001 (Section 6: Strategy Modules).

Defines the contract for quantitative trading strategies, parameter validation,
indicator calculation, and signal generation with zero forward-looking leakage.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class BaseStrategy(ABC):
    """Abstract Base Class for quantitative trading strategies."""
    
    name: str = "base_strategy"
    display_name: str = "Base Strategy"
    description: str = "Abstract quantitative strategy interface"
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """Initializes strategy with validated parameters."""
        self.params: Dict[str, Any] = self.default_parameters()
        if parameters:
            self.params.update(parameters)
        self.validate_parameters()
        
    @classmethod
    @abstractmethod
    def default_parameters(cls) -> Dict[str, Any]:
        """Returns the dictionary of default strategy parameters."""
        pass
        
    @classmethod
    @abstractmethod
    def parameter_schema(cls) -> Dict[str, Dict[str, Any]]:
        """Returns metadata schema for UI parameter controls (min, max, step, type, description)."""
        pass
        
    @abstractmethod
    def validate_parameters(self) -> None:
        """Validates that parameters are mathematically sound and within permissible ranges.
        
        Raises:
            ValueError if parameters are invalid.
        """
        pass
        
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Computes technical/quantitative indicators using historical market data.
        
        Indicators MUST strictly be causal and never reference future index positions.
        
        Parameters:
            data: Clean market DataFrame with DatetimeIndex and standard OHLCV columns.
            
        Returns:
            DataFrame with indicator columns appended.
        """
        pass
        
    @abstractmethod
    def generate_signals(self, data_with_indicators: pd.DataFrame) -> pd.Series:
        """Generates target position signals based on indicator states at each bar close.
        
        Conventions:
             1 : LONG position (buy / hold long)
             0 : CASH / NEUTRAL (flat / exit)
            -1 : SHORT position (sell / hold short)
            
        Parameters:
            data_with_indicators: DataFrame returned by calculate_indicators.
            
        Returns:
            pd.Series of integer signals (1, 0, -1) aligned with data_with_indicators.index.
        """
        pass
        
    def run_signal_generation(self, data: pd.DataFrame) -> pd.DataFrame:
        """Convenience method: calculates indicators and appends a 'signal' column.
        
        Parameters:
            data: Validated market DataFrame.
            
        Returns:
            DataFrame containing original columns, indicator columns, and 'signal'.
        """
        df = self.calculate_indicators(data)
        signals = self.generate_signals(df)
        df["signal"] = signals
        return df
