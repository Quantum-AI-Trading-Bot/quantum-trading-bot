#!/usr/bin/env python3
"""
Phase 1: Baseline Model
Simple baseline model for comparison
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class BaselineModel:
    """
    Baseline model that predicts based on simple rules
    """

    def __init__(self, strategy: str = "buy_and_hold"):
        """
        Initialize baseline model

        Args:
            strategy: Baseline strategy ('buy_and_hold', 'random', 'momentum')
        """
        self.strategy = strategy
        logger.info(f"Baseline model initialized with strategy: {strategy}")

    def fit(self, X: pd.DataFrame, y: pd.Series = None):
        """Fit baseline model (no-op for most baselines)"""
        logger.info(f"Baseline model '{self.strategy}' doesn't require training")
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions based on baseline strategy"""
        if self.strategy == "buy_and_hold":
            # Always predict 1 (buy/hold)
            return np.ones(len(X))

        elif self.strategy == "random":
            # Random predictions
            return np.random.randint(0, 2, len(X))

        elif self.strategy == "momentum":
            # Predict based on recent momentum
            if 'Returns' in X.columns:
                return (X['Returns'] > 0).astype(int).values
            else:
                return np.ones(len(X))

        else:
            raise ValueError(f"Unknown baseline strategy: {self.strategy}")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities"""
        predictions = self.predict(X)
        probas = np.zeros((len(X), 2))
        probas[np.arange(len(X)), predictions] = 1.0
        return probas
