"""Strategy Registry module for dynamic discovery and instantiation."""

from typing import Dict, Type, Any, Optional
from src.strategies.base import BaseStrategy
from src.strategies.sma_crossover import SMACrossoverStrategy
from src.strategies.rsi_strategy import RSIStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "sma_crossover": SMACrossoverStrategy,
    "rsi_strategy": RSIStrategy,
}


def register_strategy(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
    """Decorator to register a custom strategy."""
    STRATEGY_REGISTRY[cls.name] = cls
    return cls


def get_strategy(name: str, parameters: Optional[Dict[str, Any]] = None) -> BaseStrategy:
    """Instantiates a strategy by name with optional parameter overrides.
    
    Parameters:
        name: Registered strategy name (e.g., 'sma_crossover', 'rsi_strategy').
        parameters: Optional dictionary of parameter overrides.
        
    Returns:
        Configured BaseStrategy instance.
        
    Raises:
        KeyError if strategy name is not recognized.
    """
    normalized_name = name.lower().strip()
    if normalized_name not in STRATEGY_REGISTRY:
        available = list(STRATEGY_REGISTRY.keys())
        raise KeyError(f"Strategy '{name}' not found in registry. Available: {available}")
    strategy_cls = STRATEGY_REGISTRY[normalized_name]
    return strategy_cls(parameters=parameters)


def list_strategies() -> Dict[str, Dict[str, Any]]:
    """Returns metadata dictionary of all registered strategies."""
    info = {}
    for key, cls in STRATEGY_REGISTRY.items():
        info[key] = {
            "name": cls.name,
            "display_name": cls.display_name,
            "description": cls.description,
            "default_params": cls.default_parameters(),
            "parameter_schema": cls.parameter_schema(),
        }
    return info
