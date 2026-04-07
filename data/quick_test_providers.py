#!/usr/bin/env python3
"""
Quick test for Yahoo Finance and CoinGecko providers
"""

import asyncio
import sys
sys.path.append('/home/davidsanker/platform')

from data.yahoo_finance_provider import YahooFinanceProvider
from data.coingecko_provider import CoinGeckoProvider

async def quick_test():
    print("🧪 QUICK PROVIDER TEST")
    print("=" * 40)

    # Test Yahoo Finance
    print("\n1️⃣ Testing Yahoo Finance...")
    yahoo_provider = YahooFinanceProvider()
    yahoo_success = await yahoo_provider.initialize()

    if yahoo_success:
        try:
            aapl_data = await yahoo_provider.get_market_data("AAPL")
            if aapl_data:
                print(f"   ✅ AAPL: ${aapl_data.price} ({aapl_data.change_percent:+.2f}%)")
                print(f"   📊 Volume: {aapl_data.volume:,} | Cap: ${aapl_data.market_cap/1e9:.1f}B")
            else:
                print("   ❌ Failed to get AAPL data")
        except Exception as e:
            print(f"   ❌ Yahoo Finance error: {e}")
    else:
        print("   ❌ Yahoo Finance initialization failed")

    # Test CoinGecko
    print("\n2️⃣ Testing CoinGecko...")
    coingecko_provider = CoinGeckoProvider()
    coin_success = await coingecko_provider.initialize()

    if coin_success:
        try:
            # Try to get Bitcoin data using "bitcoin" as the ID
            btc_data = await coingecko_provider.get_coin_data("bitcoin")
            if btc_data:
                print(f"   ✅ BTC: ${btc_data.current_price:,.2f} ({btc_data.price_change_percentage_24h:+.2f}%)")
                print(f"   📊 Market Cap: ${btc_data.market_cap/1e9:.1f}B | Rank: #{btc_data.market_cap_rank}")
            else:
                print("   ❌ Failed to get Bitcoin data")
        except Exception as e:
            print(f"   ❌ CoinGecko error: {e}")
        finally:
            await coingecko_provider.close()
    else:
        print("   ❌ CoinGecko initialization failed")

    print(f"\n📊 RESULTS:")
    print(f"   Yahoo Finance: {'✅ WORKING' if yahoo_success else '❌ FAILED'}")
    print(f"   CoinGecko: {'✅ WORKING' if coin_success else '❌ FAILED'}")

    return yahoo_success or coin_success

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    if success:
        print(f"\n🎉 At least one provider is working!")
    else:
        print(f"\n❌ All providers failed!")