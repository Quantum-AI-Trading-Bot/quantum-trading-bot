"""
Phase 1: Strategy Module
Implements trading strategies (rule-based and model-based)
"""

from .base_strategy import BaseStrategy
from .moving_average_crossover import MovingAverageCrossover
from .strategy_manager import StrategyManager

__all__ = [
    'BaseStrategy',
    'MovingAverageCrossover',
    'StrategyManager'
]
