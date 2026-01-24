"""
Phase 1: Data Module
Handles data ingestion, cleaning, and feature engineering
"""

from .fetch_price_data import fetch_price_data, DataFetcher
from .feature_engineering import add_technical_indicators, prepare_features

__all__ = [
    'fetch_price_data',
    'DataFetcher',
    'add_technical_indicators',
    'prepare_features'
]
