"""Quantitative trading strategies package."""
from src.strategies.base import BaseStrategy
from src.strategies.sma_crossover import SMACrossoverStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.registry import get_strategy, list_strategies, register_strategy, STRATEGY_REGISTRY

__all__ = [
    "BaseStrategy",
    "SMACrossoverStrategy",
    "RSIStrategy",
    "get_strategy",
    "list_strategies",
    "register_strategy",
    "STRATEGY_REGISTRY",
]
