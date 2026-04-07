#!/usr/bin/env python3
"""
NewsAPI Provider for Financial News Sentiment Analysis
Integrates with NewsAPI for real-time news sentiment tracking
"""

import requests
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NewsSentimentData:
    """News sentiment analysis data"""
    symbol: str
    timestamp: datetime
    sentiment_score: float  # -1 to 1
    article_count: int
    top_headlines: List[str]
    keywords: List[str]

class NewsAPIProvider:
    """NewsAPI provider for news sentiment analysis"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.session = requests.Session()

    def get_symbol_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get news sentiment for a symbol"""
        try:
            # Search for news about the symbol
            url = f"{self.base_url}/everything"
            params = {
                'q': f'{symbol} OR "{symbol} stock" OR "{symbol} corporation"',
                'sortBy': 'relevancy',
                'language': 'en',
                'pageSize': 20,
                'apiKey': self.api_key
            }

            response = self.session.get(url, params=params, timeout=10)

            # Check for rate limit before raising status error
            if response.status_code == 429:
                logger.warning(f"NewsAPI rate limit hit for {symbol}, using neutral sentiment")
                return {
                    'symbol': symbol,
                    'sentiment_score': 0.0,
                    'article_count': 0,
                    'top_headlines': [],
                    'keywords': [],
                    'rate_limited': True
                }

            response.raise_for_status()

            data = response.json()

            if data.get('status') != 'ok':
                logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return None

            articles = data.get('articles', [])
            if not articles:
                return {
                    'symbol': symbol,
                    'sentiment_score': 0.0,
                    'article_count': 0,
                    'top_headlines': [],
                    'keywords': []
                }

            # Simple sentiment analysis based on headlines
            positive_words = ['up', 'rise', 'gain', 'growth', 'profit', 'bull', 'buy', 'strong']
            negative_words = ['down', 'fall', 'loss', 'decline', 'bear', 'sell', 'weak', 'crash']

            sentiment_scores = []
            headlines = []

            for article in articles[:10]:  # Analyze top 10 articles
                title = (article.get('title') or '').lower()
                description = (article.get('description') or '').lower()
                text = f"{title} {description}"

                headlines.append(article.get('title') or 'N/A')

                # Calculate simple sentiment
                positive_count = sum(1 for word in positive_words if word in text)
                negative_count = sum(1 for word in negative_words if word in text)

                if positive_count > negative_count:
                    sentiment_scores.append(min(1.0, (positive_count - negative_count) / 5.0))
                elif negative_count > positive_count:
                    sentiment_scores.append(max(-1.0, -(negative_count - positive_count) / 5.0))
                else:
                    sentiment_scores.append(0.0)

            # Calculate overall sentiment
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0

            return {
                'symbol': symbol,
                'sentiment_score': avg_sentiment,
                'article_count': len(articles),
                'top_headlines': headlines[:5],
                'keywords': []
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limit hit - return neutral sentiment
                logger.warning(f"NewsAPI rate limit hit for {symbol}, using cached/neutral data")
                return {
                    'symbol': symbol,
                    'sentiment_score': 0.0,
                    'article_count': 0,
                    'top_headlines': [],
                    'keywords': [],
                    'rate_limited': True
                }
            else:
                logger.error(f"HTTP error getting NewsAPI sentiment for {symbol}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error getting NewsAPI sentiment for {symbol}: {e}")
            return None