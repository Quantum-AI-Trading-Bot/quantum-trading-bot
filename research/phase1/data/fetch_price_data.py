#!/usr/bin/env python3
"""
Phase 1: Data Fetching Module
Downloads and caches OHLCV data from multiple sources with robust error handling
"""

import os
import pandas as pd
import yfinance as yf
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import pickle
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Robust data fetching with caching, retry logic, and multiple data sources
    """

    def __init__(self, cache_dir: str = None, cache_expiry_hours: int = 24):
        """
        Initialize DataFetcher with caching support

        Args:
            cache_dir: Directory to cache downloaded data
            cache_expiry_hours: Hours before cache expires
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_expiry_hours = cache_expiry_hours

        logger.info(f"DataFetcher initialized with cache: {self.cache_dir}")

    def _get_cache_path(self, symbol: str, start_date: str, end_date: str) -> Path:
        """Generate cache file path for symbol and date range"""
        safe_symbol = symbol.replace('/', '_').replace('^', '_')
        cache_filename = f"{safe_symbol}_{start_date}_{end_date}.pkl"
        return self.cache_dir / cache_filename

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired"""
        if not cache_path.exists():
            return False

        file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_time = datetime.now() - timedelta(hours=self.cache_expiry_hours)

        return file_mtime > expiry_time

    def _load_from_cache(self, cache_path: Path) -> Optional[pd.DataFrame]:
        """Load data from cache file"""
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            logger.info(f"Loaded {len(data)} rows from cache: {cache_path.name}")
            return data
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}")
            return None

    def _save_to_cache(self, data: pd.DataFrame, cache_path: Path):
        """Save data to cache file"""
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"Saved {len(data)} rows to cache: {cache_path.name}")
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_path}: {e}")

    def fetch_yfinance_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = '1d',
        retry_attempts: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data from Yahoo Finance with retry logic

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'SPY')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval ('1d', '1h', '5m', etc.)
            retry_attempts: Number of retry attempts on failure

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        cache_path = self._get_cache_path(symbol, start_date, end_date)

        # Check cache first
        if self._is_cache_valid(cache_path):
            cached_data = self._load_from_cache(cache_path)
            if cached_data is not None:
                return cached_data

        # Fetch from Yahoo Finance with retries
        for attempt in range(retry_attempts):
            try:
                logger.info(f"Fetching {symbol} from Yahoo Finance (attempt {attempt + 1}/{retry_attempts})")

                ticker = yf.Ticker(symbol)
                data = ticker.history(start=start_date, end=end_date, interval=interval)

                if data.empty:
                    logger.warning(f"No data returned for {symbol}")
                    return None

                # Validate data
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in data.columns for col in required_columns):
                    logger.error(f"Missing required columns for {symbol}")
                    return None

                # Clean column names
                data.columns = data.columns.str.strip()

                # Add metadata
                data['Symbol'] = symbol
                data['Data_Source'] = 'Yahoo Finance'
                data['Fetch_Date'] = datetime.now()

                logger.info(f"Successfully fetched {len(data)} rows for {symbol}")

                # Save to cache
                self._save_to_cache(data, cache_path)

                return data

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < retry_attempts - 1:
                    import time
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {retry_attempts} attempts failed for {symbol}")
                    return None

        return None

    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str = '1d'
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols

        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        results = {}

        for symbol in symbols:
            logger.info(f"Fetching {symbol}...")
            data = self.fetch_yfinance_data(symbol, start_date, end_date, interval)
            if data is not None:
                results[symbol] = data
            else:
                logger.warning(f"Failed to fetch data for {symbol}")

        logger.info(f"Successfully fetched {len(results)}/{len(symbols)} symbols")
        return results

    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate fetched data for quality issues

        Args:
            data: DataFrame to validate

        Returns:
            True if data passes validation, False otherwise
        """
        checks = []

        # Check for missing values
        missing_pct = data.isnull().sum() / len(data) * 100
        if (missing_pct > 10).any():
            logger.warning(f"High missing values: {missing_pct[missing_pct > 10].to_dict()}")
            checks.append(False)
        else:
            checks.append(True)

        # Check for zero prices
        if (data['Close'] <= 0).any():
            logger.error(f"Invalid prices (<= 0) found in data")
            checks.append(False)
        else:
            checks.append(True)

        # Check for zero volume
        if (data['Volume'] < 0).any():
            logger.error(f"Negative volume found in data")
            checks.append(False)
        else:
            checks.append(True)

        # Check data length
        if len(data) < 100:
            logger.warning(f"Low data length: {len(data)} rows")
            checks.append(False)
        else:
            checks.append(True)

        return all(checks)

    def get_data_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics for fetched data

        Args:
            data: DataFrame to summarize

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'rows': len(data),
            'columns': len(data.columns),
            'date_range': {
                'start': str(data.index.min()) if len(data) > 0 else None,
                'end': str(data.index.max()) if len(data) > 0 else None
            },
            'price_stats': {
                'mean': float(data['Close'].mean()) if len(data) > 0 else None,
                'std': float(data['Close'].std()) if len(data) > 0 else None,
                'min': float(data['Close'].min()) if len(data) > 0 else None,
                'max': float(data['Close'].max()) if len(data) > 0 else None
            },
            'volume_stats': {
                'mean': float(data['Volume'].mean()) if len(data) > 0 else None,
                'median': float(data['Volume'].median()) if len(data) > 0 else None
            },
            'missing_values': data.isnull().sum().to_dict()
        }

        return summary


def fetch_price_data(
    symbol: str,
    start_date: str,
    end_date: str = None,
    interval: str = '1d',
    cache_dir: str = None,
    validate: bool = True
) -> Optional[pd.DataFrame]:
    """
    Convenience function to fetch price data for a single symbol

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'SPY')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to today
        interval: Data interval ('1d', '1h', etc.)
        cache_dir: Directory for caching data
        validate: Whether to validate data quality

    Returns:
        DataFrame with OHLCV data or None if failed
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    fetcher = DataFetcher(cache_dir=cache_dir)
    data = fetcher.fetch_yfinance_data(symbol, start_date, end_date, interval)

    if data is not None and validate:
        if not fetcher.validate_data(data):
            logger.warning(f"Data validation failed for {symbol}")
            return None

    return data


if __name__ == "__main__":
    # Test the data fetcher
    logger.info("Testing Data Fetcher...")

    # Test single symbol
    symbol = "AAPL"
    start_date = "2024-01-01"
    end_date = "2025-01-01"

    logger.info(f"\n{'='*60}")
    logger.info(f"Fetching {symbol} from {start_date} to {end_date}")
    logger.info(f"{'='*60}\n")

    data = fetch_price_data(symbol, start_date, end_date)

    if data is not None:
        logger.info(f"\n✅ Successfully fetched {len(data)} rows")
        logger.info(f"\nData Preview:")
        logger.info(data.head())

        logger.info(f"\nData Summary:")
        fetcher = DataFetcher()
        summary = fetcher.get_data_summary(data)
        logger.info(json.dumps(summary, indent=2))

        logger.info(f"\nData Statistics:")
        logger.info(data.describe())
    else:
        logger.error(f"❌ Failed to fetch data for {symbol}")
