#!/usr/bin/env python3
"""
FRED (Federal Reserve Economic Data) Provider
Provides economic indicators for market context analysis
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FREDDataProvider:
    """FRED economic data provider"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = requests.Session()

    def get_series(self, series_id: str, limit: int = 1) -> Optional[float]:
        """Get latest value for a FRED series"""
        try:
            url = f"{self.base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': str(limit),
                'sort_order': 'desc'
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'observations' not in data or not data['observations']:
                return None

            latest_observation = data['observations'][0]
            return float(latest_observation['value'])

        except Exception as e:
            logger.error(f"Error getting FRED series {series_id}: {e}")
            return None