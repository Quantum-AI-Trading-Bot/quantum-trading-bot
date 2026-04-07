#!/usr/bin/env python3
"""
Comprehensive Open Source Data Sources for Trading
Collection of free, high-quality APIs and data feeds for enhanced trading intelligence
"""

from typing import Dict, List, Any
from datetime import datetime
import json

class OpenSourceDataCatalog:
    """Catalog of open source data sources for trading algorithms"""

    def __init__(self):
        self.data_sources = self._initialize_data_sources()

    def _initialize_data_sources(self) -> Dict[str, List[Dict]]:
        """Initialize comprehensive list of open source data sources"""
        return {
            "market_data": [
                {
                    "name": "Alpha Vantage",
                    "description": "Free real-time and historical market data",
                    "api_url": "https://www.alphavantage.co/",
                    "free_tier": "500 calls/day, 5 calls/minute",
                    "data_types": ["stocks", "forex", "crypto", "technical_indicators"],
                    "key_features": ["Real-time quotes", "Historical data", "Technical indicators", "Sector performance"],
                    "api_key_required": True,
                    "priority": "HIGH",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "Yahoo Finance API (yfinance)",
                    "description": "Unofficial Python library for Yahoo Finance data",
                    "api_url": "https://github.com/ranaroussi/yfinance",
                    "free_tier": "Unlimited (rate-limited by Yahoo)",
                    "data_types": ["stocks", "etfs", "crypto", "forex", "options"],
                    "key_features": ["Real-time data", "Historical data", "Fundamentals", "Options chains"],
                    "api_key_required": False,
                    "priority": "HIGH",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "Polygon.io",
                    "description": "Free end-of-day stock market data",
                    "api_url": "https://polygon.io/",
                    "free_tier": "5 calls/minute, end-of-day data only",
                    "data_types": ["stocks", "forex", "crypto", "options"],
                    "key_features": ["EOD data", "Splits/dividends", "Market status", "Company info"],
                    "api_key_required": True,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "IEX Cloud",
                    "description": "Financial data with generous free tier",
                    "api_url": "https://iexcloud.io/",
                    "free_tier": "50,000 messages/month",
                    "data_types": ["stocks", "etfs", "crypto", "market_data"],
                    "key_features": ["Real-time prices", "Company fundamentals", "News sentiment", "Social sentiment"],
                    "api_key_required": True,
                    "priority": "HIGH",
                    "integration_difficulty": "Medium"
                }
            ],

            "cryptocurrency": [
                {
                    "name": "CoinGecko API",
                    "description": "Free cryptocurrency market data",
                    "api_url": "https://www.coingecko.com/api/documentations/v3",
                    "free_tier": "10-50 calls/minute (no API key needed)",
                    "data_types": ["crypto_prices", "market_data", "defi", "nft"],
                    "key_features": ["Price data", "Market cap", "Trading volume", "Developer data", "Social data"],
                    "api_key_required": False,
                    "priority": "HIGH",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "CoinMarketCap",
                    "description": "Leading cryptocurrency data provider",
                    "api_url": "https://coinmarketcap.com/api/",
                    "free_tier": "10,000 calls/month",
                    "data_types": ["crypto_prices", "market_data", "blockchain_stats"],
                    "key_features": ["Price tracking", "Market rankings", "Blockchain metrics", "Converter API"],
                    "api_key_required": True,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "CryptoCompare API",
                    "description": "Comprehensive cryptocurrency data",
                    "api_url": "https://min-api.cryptocompare.com/",
                    "free_tier": "100,000 calls/month",
                    "data_types": ["crypto_prices", "social_sentiment", "blockchain_data"],
                    "key_features": ["OHLCV data", "Social sentiment", "News integration", "Mining data"],
                    "api_key_required": True,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                }
            ],

            "economic_data": [
                {
                    "name": "World Bank Open Data",
                    "description": "Global economic development data",
                    "api_url": "https://data.worldbank.org/",
                    "free_tier": "Unlimited",
                    "data_types": ["economic_indicators", "development_metrics", "global_markets"],
                    "key_features": ["GDP data", "Inflation rates", "Trade statistics", "Interest rates"],
                    "api_key_required": False,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Medium"
                },
                {
                    "name": "Eurostat Open Data",
                    "description": "European Union statistical data",
                    "api_url": "https://ec.europa.eu/eurostat/data/database",
                    "free_tier": "Unlimited",
                    "data_types": ["eu_economics", "inflation", "employment", "trade"],
                    "key_features": ["EU economic indicators", "Country comparisons", "Seasonally adjusted data"],
                    "api_key_required": False,
                    "priority": "LOW",
                    "integration_difficulty": "Medium"
                },
                {
                    "name": "Bureau of Labor Statistics (BLS)",
                    "description": "US employment and price data",
                    "api_url": "https://www.bls.gov/developers/",
                    "free_tier": "Unlimited",
                    "data_types": ["employment", "inflation", "wages", "productivity"],
                    "key_features": ["CPI data", "Unemployment rates", "Wage growth", "Industry statistics"],
                    "api_key_required": False,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Medium"
                }
            ],

            "sentiment_analysis": [
                {
                    "name": "Reddit API (PRAW)",
                    "description": "Reddit social sentiment data",
                    "api_url": "https://www.reddit.com/dev/api/",
                    "free_tier": "60 calls/minute",
                    "data_types": ["social_sentiment", "discussion_trends", "wallstreetbets"],
                    "key_features": ["WallStreetBets sentiment", "Stock discussion trends", "Meme stock tracking"],
                    "api_key_required": True,
                    "priority": "HIGH",
                    "integration_difficulty": "Medium"
                },
                {
                    "name": "Twitter API v2 (Free)",
                    "description": "Twitter/X social sentiment and trending topics",
                    "api_url": "https://developer.twitter.com/en/docs/twitter-api",
                    "free_tier": "500,000 tweets/month",
                    "data_types": ["social_sentiment", "trending_topics", "influencer_tweets"],
                    "key_features": ["Real-time sentiment", "Trending stocks", "Influencer tracking", "Breaking news"],
                    "api_key_required": True,
                    "priority": "HIGH",
                    "integration_difficulty": "Medium"
                },
                {
                    "name": "StockTwits API",
                    "description": "Financial social media sentiment",
                    "api_url": "https://api.stocktwits.com/developers/docs/api",
                    "free_tier": "200 requests/hour",
                    "data_types": ["social_sentiment", "trader_sentiment", "bull_bear_signals"],
                    "key_features": ["Trader sentiment", "Bull/Bear signals", "Stock discussions", "Watchlist tracking"],
                    "api_key_required": False,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                }
            ],

            "alternative_data": [
                {
                    "name": "Google Trends API (pytrends)",
                    "description": "Google search interest data for stocks",
                    "api_url": "https://pypi.org/project/pytrends/",
                    "free_tier": "Unlimited (rate-limited)",
                    "data_types": ["search_trends", "interest_over_time", "related_queries"],
                    "key_features": ["Stock search interest", "Economic trend tracking", "Brand awareness"],
                    "api_key_required": False,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "SEC EDGAR Database",
                    "description": "Company filings and insider trading data",
                    "api_url": "https://www.sec.gov/edgar/sec-api-documentation",
                    "free_tier": "10 requests/second",
                    "data_types": ["company_filings", "insider_trading", "quarterly_reports"],
                    "key_features": ["10-K/10-Q filings", "Insider trading forms", "Executive compensation"],
                    "api_key_required": False,
                    "priority": "HIGH",
                    "integration_difficulty": "Medium"
                },
                {
                    "name": "Quandl (Nasdaq Data Link)",
                    "description": "Alternative financial data provider",
                    "api_url": "https://data.nasdaq.com/",
                    "free_tier": "50 calls/day",
                    "data_types": ["economic_data", "alternative_data", "financial_metrics"],
                    "key_features": ["Economic indicators", "Real estate data", "Commodity prices", "Credit ratings"],
                    "api_key_required": True,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                }
            ],

            "news_data": [
                {
                    "name": "GNews API",
                    "description": "Free news aggregation API",
                    "api_url": "https://gnews.io/",
                    "free_tier": "100 articles/day",
                    "data_types": ["financial_news", "market_news", "company_news"],
                    "key_features": ["Real-time news", "Topic filtering", "Language support", "Source variety"],
                    "api_key_required": True,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "Guardian API",
                    "description": "The Guardian newspaper open API",
                    "api_url": "https://open-platform.theguardian.com/",
                    "free_tier": "5,000 calls/day",
                    "data_types": ["news_articles", "business_news", "financial_markets"],
                    "key_features": ["Business news", "Financial markets", "Economic coverage", "Tag-based search"],
                    "api_key_required": True,
                    "priority": "LOW",
                    "integration_difficulty": "Easy"
                },
                {
                    "name": "New York Times API",
                    "description": "NYTimes open news API",
                    "api_url": "https://developer.nytimes.com/",
                    "free_tier": "1,000 calls/day",
                    "data_types": ["news_articles", "business_news", "market_analysis"],
                    "key_features": ["Business section", "Market news", "Economic analysis", "Company coverage"],
                    "api_key_required": True,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                }
            ],

            "options_data": [
                {
                    "name": "OptionsDX",
                    "description": "Free options data and analytics",
                    "api_url": "https://www.optionsdx.com/api/",
                    "free_tier": "Limited free tier",
                    "data_types": ["options_chains", "implied_volatility", "options_greeks"],
                    "key_features": ["Options chains", "IV rankings", "Straddles", "Volume analysis"],
                    "api_key_required": True,
                    "priority": "LOW",
                    "integration_difficulty": "Medium"
                },
                {
                    "name": "MarketChameleon (Free Tier)",
                    "description": "Options flow and unusual activity detection",
                    "api_url": "https://www.marketchameleon.com/",
                    "free_tier": "Limited features",
                    "data_types": ["options_flow", "unusual_activity", "iv_rankings"],
                    "key_features": ["Unusual options activity", "IV percentiles", "Max pain calculations"],
                    "api_key_required": False,
                    "priority": "LOW",
                    "integration_difficulty": "Hard"
                }
            ],

            "commodities_data": [
                {
                    "name": "EIA (Energy Information Administration)",
                    "description": "US energy statistics and data",
                    "api_url": "https://www.eia.gov/opendata/",
                    "free_tier": "Unlimited",
                    "data_types": ["energy_prices", "oil_gas", "renewable_energy"],
                    "key_features": ["Oil prices", "Natural gas data", "Electricity markets", "Petroleum statistics"],
                    "api_key_required": False,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Medium"
                },
                {
                    "name": "USDA Economic Research Service",
                    "description": "Agricultural commodity data",
                    "api_url": "https://www.ers.usda.gov/data-products/",
                    "free_tier": "Unlimited",
                    "data_types": ["agriculture", "food_prices", "crop_data"],
                    "key_features": ["Crop prices", "Food inflation", "Supply/demand data", "Export statistics"],
                    "api_key_required": False,
                    "priority": "LOW",
                    "integration_difficulty": "Medium"
                }
            ],

            "forex_data": [
                {
                    "name": "ForexFactory Calendar API",
                    "description": "Forex economic calendar and news",
                    "api_url": "https://www.forexfactory.com/",
                    "free_tier": "Unofficial scraping required",
                    "data_types": ["economic_calendar", "forex_news", "central_bank_announcements"],
                    "key_features": ["High-impact news", "Central bank meetings", "Economic indicators", "Market hours"],
                    "api_key_required": False,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Hard"
                },
                {
                    "name": "OANDA Exchange Rates API",
                    "description": "Free foreign exchange rates",
                    "api_url": "https://developer.oanda.com/",
                    "free_tier": "1,000 calls/day",
                    "data_types": ["fx_rates", "currency_conversion", "historical_rates"],
                    "key_features": ["Real-time rates", "Historical data", "Currency conversion", "Forward rates"],
                    "api_key_required": True,
                    "priority": "MEDIUM",
                    "integration_difficulty": "Easy"
                }
            ]
        }

    def get_priority_recommendations(self) -> Dict[str, List[Dict]]:
        """Get prioritized recommendations for data source integration"""
        priorities = {"HIGH": [], "MEDIUM": [], "LOW": []}

        for category, sources in self.data_sources.items():
            for source in sources:
                priority = source["priority"]
                priorities[priority].append({
                    **source,
                    "category": category,
                    "integration_priority": self._calculate_integration_score(source)
                })

        # Sort by integration priority within each priority level
        for priority in priorities:
            priorities[priority].sort(key=lambda x: x["integration_priority"], reverse=True)

        return priorities

    def _calculate_integration_score(self, source: Dict) -> float:
        """Calculate integration priority score (0-100)"""
        score = 0

        # Base score for priority level
        priority_scores = {"HIGH": 70, "MEDIUM": 40, "LOW": 10}
        score += priority_scores.get(source["priority"], 0)

        # API key requirement (free vs paid preference)
        if not source["api_key_required"]:
            score += 15

        # Integration difficulty
        difficulty_scores = {"Easy": 10, "Medium": 5, "Hard": 0}
        score += difficulty_scores.get(source["integration_difficulty"], 0)

        # Data variety bonus
        data_types = len(source["data_types"])
        score += min(data_types * 2, 15)

        return min(score, 100)

    def get_implementation_roadmap(self) -> List[Dict]:
        """Get recommended implementation roadmap"""
        recommendations = self.get_priority_recommendations()

        roadmap = []
        # Phase 1: High priority, easy integration
        for source in recommendations["HIGH"]:
            if source["integration_difficulty"] == "Easy":
                roadmap.append({
                    **source,
                    "phase": 1,
                    "estimated_days": 1,
                    "resources_needed": "API key, basic Python requests"
                })

        # Phase 2: High priority, medium integration
        for source in recommendations["HIGH"]:
            if source["integration_difficulty"] == "Medium":
                roadmap.append({
                    **source,
                    "phase": 2,
                    "estimated_days": 2-3,
                    "resources_needed": "API key, authentication setup"
                })

        # Phase 3: Medium priority, easy integration
        for source in recommendations["MEDIUM"]:
            if source["integration_difficulty"] == "Easy":
                roadmap.append({
                    **source,
                    "phase": 3,
                    "estimated_days": 1,
                    "resources_needed": "Optional API key"
                })

        return sorted(roadmap, key=lambda x: x["phase"])

    def export_catalog(self, filename: str = None) -> str:
        """Export the data catalog to JSON file"""
        if filename is None:
            filename = f"data_catalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_data = {
            "generated_at": datetime.now().isoformat(),
            "total_sources": sum(len(sources) for sources in self.data_sources.values()),
            "data_sources": self.data_sources,
            "recommendations": self.get_priority_recommendations(),
            "roadmap": self.get_implementation_roadmap()
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        return filename

def main():
    """Display comprehensive open source data source recommendations"""
    catalog = OpenSourceDataCatalog()

    print("🚀 COMPREHENSIVE OPEN SOURCE DATA SOURCES FOR TRADING")
    print("=" * 70)

    # Display recommendations by priority
    recommendations = catalog.get_priority_recommendations()

    print("\n🎯 HIGH PRIORITY RECOMMENDATIONS (Implement First):")
    print("=" * 55)

    for i, source in enumerate(recommendations["HIGH"][:10], 1):
        print(f"\n{i}. 📊 {source['name']} ({source['category'].replace('_', ' ').title()})")
        print(f"   💡 {source['description']}")
        print(f"   ✨ Key Features: {', '.join(source['key_features'][:3])}")
        print(f"   🆓 Free Tier: {source['free_tier']}")
        print(f"   🔑 API Key: {'Required' if source['api_key_required'] else 'Not Required'}")
        print(f"   📈 Integration: {source['integration_difficulty']} (Score: {source['integration_priority']}/100)")
        print(f"   🔗 {source['api_url']}")

    print(f"\n📋 IMPLEMENTATION ROADMAP:")
    print("=" * 50)

    roadmap = catalog.get_implementation_roadmap()
    current_phase = 0

    for i, source in enumerate(roadmap[:8], 1):
        if source["phase"] != current_phase:
            current_phase = source["phase"]
            print(f"\n📅 Phase {current_phase}:")

        print(f"   {i}. {source['name']} - {source['estimated_days']} day(s)")

    # Export catalog
    filename = catalog.export_catalog()
    print(f"\n💾 Full catalog exported to: {filename}")

    print(f"\n🎯 NEXT STEPS:")
    print("   1. Choose 2-3 HIGH priority sources to start")
    print("   2. Get API keys for required services")
    print("   3. Implement using existing data source framework")
    print("   4. Test integration with trading algorithm")
    print("   5. Monitor performance and add more sources")

    print(f"\n📊 SUMMARY: {len(recommendations['HIGH'])} HIGH | {len(recommendations['MEDIUM'])} MEDIUM | {len(recommendations['LOW'])} LOW priority sources")

if __name__ == "__main__":
    main()