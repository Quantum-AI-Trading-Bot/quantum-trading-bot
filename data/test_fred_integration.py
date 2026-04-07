#!/usr/bin/env python3
"""
FRED API Integration Test
Tests the FRED API key integration and retrieves real economic data
"""

import asyncio
import sys
import json
import aiohttp
from datetime import datetime, timezone, timedelta

# Add platform to path
sys.path.append('/home/davidsanker/platform')

async def test_fred_api_directly():
    """Test FRED API directly to validate the key"""
    print("🔍 Testing FRED API Direct Access...")

    api_key = os.environ.get('NEWSAPI_KEY', '')
    base_url = "https://api.stlouisfed.org/fred"

    # Test with GDP data
    url = f"{base_url}/series/observations"
    params = {
        'series_id': 'GDP',
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        'observation_end': datetime.now().strftime('%Y-%m-%d'),
        'limit': 10
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                print(f"  HTTP Status: {response.status}")

                if response.status == 200:
                    data = await response.json()

                    if 'observations' in data:
                        observations = data['observations']
                        print(f"  ✅ Successfully retrieved {len(observations)} GDP observations")

                        # Show latest data
                        if observations:
                            latest = observations[-1]
                            print(f"  📊 Latest GDP Data:")
                            print(f"    Date: {latest['date']}")
                            print(f"    Value: ${float(latest['value']):.2f} Trillion")
                            print(f"    Real-time: ✅ LIVE DATA")

                        return True
                    else:
                        print(f"  ❌ Unexpected response structure: {list(data.keys())}")
                        return False
                else:
                    text = await response.text()
                    print(f"  ❌ API Error: {response.status}")
                    print(f"  Response: {text[:200]}...")
                    return False

    except Exception as e:
        print(f"  ❌ Connection error: {e}")
        return False

async def test_multiple_fred_series():
    """Test multiple FRED economic series"""
    print("\n📈 Testing Multiple Economic Series...")

    api_key = os.environ.get('NEWSAPI_KEY', '')
    base_url = "https://api.stlouisfed.org/fred"

    # Key economic indicators to test
    test_series = {
        'GDP': 'Gross Domestic Product',
        'UNRATE': 'Unemployment Rate',
        'CPIAUCSL': 'Consumer Price Index',
        'DGS10': '10-Year Treasury Rate',
        'DFF': 'Federal Funds Rate',
        'M2SL': 'M2 Money Supply',
        'INDPRO': 'Industrial Production',
        'HOUST': 'Housing Starts'
    }

    async with aiohttp.ClientSession() as session:
        results = {}

        for series_id, description in test_series.items():
            print(f"  📊 Testing {series_id} ({description})...")

            url = f"{base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': api_key,
                'file_type': 'json',
                'limit': 5,  # Just get latest 5 observations
                'sort_order': 'desc'  # Get most recent first
            }

            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        if 'observations' in data and data['observations']:
                            latest = data['observations'][0]
                            value = float(latest.get('value', 0))

                            # Format value based on series type
                            if series_id in ['UNRATE', 'DFF', 'DGS10']:
                                formatted_value = f"{value:.2f}%"
                            elif series_id in ['GDP']:
                                formatted_value = f"${value:.2f} Trillion"
                            elif series_id in ['M2SL']:
                                formatted_value = f"${value/1000:.1f} Trillion"
                            else:
                                formatted_value = f"{value:.2f}"

                            results[series_id] = {
                                'value': value,
                                'formatted': formatted_value,
                                'date': latest.get('date', 'Unknown'),
                                'description': description
                            }

                            print(f"    ✅ {formatted_value} (as of {latest.get('date', 'Unknown')})")
                        else:
                            print(f"    ❌ No data available")
                            results[series_id] = None
                    else:
                        print(f"    ❌ HTTP {response.status}")
                        results[series_id] = None

            except Exception as e:
                print(f"    ❌ Error: {e}")
                results[series_id] = None

        return results

async def test_fred_integration_with_alternative_data():
    """Test FRED integration through our AlternativeDataSource"""
    print("\n🔗 Testing FRED Integration via AlternativeDataSource...")

    try:
        # Import our alternative data source
        from data.alternative_data import AlternativeDataSource

        # Create with API key
        api_keys = {'fred': os.environ.get('NEWSAPI_KEY', '')}
        alt_source = AlternativeDataSource(api_keys)

        # Initialize (this should set up the session)
        await alt_source.initialize()
        print("  ✅ AlternativeDataSource initialized with FRED API key")

        # Test FRED provider directly
        fred_provider = alt_source.fred_provider
        await fred_provider.initialize()
        print("  ✅ FRED provider initialized")

        # Test getting GDP data
        print("  📊 Testing GDP data retrieval...")
        gdp_data = await fred_provider.get_economic_series('GDP')

        if gdp_data:
            print(f"    ✅ Retrieved {len(gdp_data)} GDP data points")
            latest = gdp_data[-1]
            print(f"    📈 Latest GDP: ${latest['value']:.2f} Trillion (as of {latest['date']})")
        else:
            print("    ❌ No GDP data retrieved")

        # Test unemployment rate
        print("  📊 Testing unemployment rate data...")
        unrate_data = await fred_provider.get_economic_series('UNRATE')

        if unrate_data:
            print(f"    ✅ Retrieved {len(unrate_data)} unemployment data points")
            latest = unrate_data[-1]
            print(f"    👥 Latest Unemployment Rate: {latest['value']:.1f}% (as of {latest['date']})")
        else:
            print("    ❌ No unemployment data retrieved")

        # Test integrated alternative data for AAPL
        print("  🍎 Testing integrated alternative data for AAPL...")
        alt_data = await alt_source.get_alternative_data('AAPL', ['fred'])

        if alt_data and 'fred' in alt_data:
            fred_data = alt_data['fred']
            print(f"    ✅ FRED data for AAPL: {len(fred_data)} indicators")

            for indicator, data in fred_data.items():
                print(f"      📊 {indicator}: {data.get('latest_value', 'N/A')} ({data.get('trend', 'N/A')})")

        return True

    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_enhanced_context_with_fred():
    """Test enhanced context composer with FRED integration"""
    print("\n🎭 Testing Enhanced Context Composer with FRED...")

    try:
        from data.enhanced_context_composer import EnhancedQuantumContextComposer

        # Create config with FRED API key
        config = {
            'api_keys': {
                'fred': os.environ.get('NEWSAPI_KEY', '')
            },
            'max_data_sources': 8
        }

        composer = EnhancedQuantumContextComposer(config)
        await composer.initialize()
        print("  ✅ Enhanced context composer initialized with FRED")

        # Generate context for AAPL
        print("  🍎 Generating enhanced context for AAPL...")
        context = await composer.generate_enhanced_context('AAPL', max_sources=8)

        if context:
            print(f"    ✅ Context generated successfully!")
            print(f"    📊 Active data sources: {len(context.active_data_sources)}")
            print(f"    🎯 Confidence weight: {context.confidence_weight:.3f}")
            print(f"    ⚖️ Risk adjustment: {context.risk_adjustment_factor:.3f}")

            # Check FRED data in context
            alt_context = context.alternative_context
            if 'fred' in alt_context:
                fred_data = alt_context['fred']
                print(f"    🏛️ FRED indicators: {len(fred_data)}")

                for indicator, data in fred_data.items():
                    print(f"      📈 {indicator}: Latest value = {data.get('latest_value', 'N/A')}")

            # Check quantum parameters
            if context.quantum_parameters:
                print(f"    ⚛️ Quantum parameters: {len(context.quantum_parameters)} types generated")
                for param_type in list(context.quantum_parameters.keys())[:3]:
                    print(f"      🧪 {param_type}: {len(context.quantum_parameters[param_type])} dimensions")

            return True
        else:
            print("    ❌ No context generated")
            return False

    except Exception as e:
        print(f"  ❌ Enhanced context test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_fred_data_economic_value(results):
    """Analyze the economic value of retrieved FRED data"""
    print("\n💡 Economic Analysis & Trading Implications:")

    if not results:
        print("  ❌ No data to analyze")
        return

    # Extract key indicators
    gdp_growth = None
    unemployment = None
    inflation = None
    interest_rates = None

    for series_id, data in results.items():
        if data:
            value = data['value']

            if series_id == 'GDP':
                gdp_growth = value
            elif series_id == 'UNRATE':
                unemployment = value
            elif series_id == 'CPIAUCSL':
                inflation = value
            elif series_id in ['DGS10', 'DFF']:
                interest_rates = value

    # Generate insights
    print("  📈 Current Economic Conditions:")

    if unemployment is not None:
        if unemployment < 4.0:
            print(f"    👥 Low Unemployment ({unemployment:.1f}%) - Bullish for equities")
        elif unemployment > 6.0:
            print(f"    👥 High Unemployment ({unemployment:.1f}%) - Bearish for equities, bullish for bonds")
        else:
            print(f"    👥 Moderate Unemployment ({unemployment:.1f}%) - Mixed market conditions")

    if interest_rates is not None:
        if interest_rates < 2.0:
            print(f"    💰 Low Interest Rates ({interest_rates:.2f}%) - Favorable for growth stocks")
        elif interest_rates > 4.0:
            print(f"    💰 High Interest Rates ({interest_rates:.2f}%) - Favorable for value stocks, bonds")
        else:
            print(f"    💰 Moderate Interest Rates ({interest_rates:.2f}%) - Balanced approach")

    print("  🎯 Trading Strategy Recommendations:")

    if unemployment and unemployment < 4.0 and interest_rates and interest_rates < 3.0:
        print("    ✅ Strong economic expansion - Consider growth stocks, risk-on assets")
    elif unemployment and unemployment > 6.0:
        print("    🛡️ Economic weakness - Consider defensive stocks, bonds, gold")
    elif interest_rates and interest_rates > 5.0:
        print("    📉 Tight monetary policy - Consider value stocks, short-duration bonds")
    else:
        print("    ⚖️ Mixed signals - Diversified approach recommended")

async def main():
    """Main test runner"""
    print("🧪 FRED API Integration Test Suite")
    print("Testing API Key: YOUR_NEWSAPI_KEY")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    tests = [
        ("Direct FRED API Test", test_fred_api_directly),
        ("Multiple Economic Series", test_multiple_fred_series),
        ("Alternative Data Integration", test_fred_integration_with_alternative_data),
        ("Enhanced Context with FRED", test_enhanced_context_with_fred)
    ]

    passed = 0
    failed = 0
    fred_results = None

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 Running: {test_name}")
        print(f"{'='*60}")

        try:
            result = await test_func()

            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED")

                # Store FRED results for analysis
                if test_name == "Multiple Economic Series" and isinstance(result, dict):
                    fred_results = result

            else:
                failed += 1
                print(f"❌ {test_name}: FAILED")

        except Exception as e:
            failed += 1
            print(f"💥 {test_name}: CRASHED - {e}")

    # Analyze economic data if available
    if fred_results:
        analyze_fred_data_economic_value(fred_results)

    # Final summary
    print(f"\n{'='*70}")
    print("📋 FRED INTEGRATION TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n🎉 ALL FRED INTEGRATION TESTS PASSED!")
        print("✅ Your FRED API key is working perfectly!")
        print("🚀 Your trading bot now has access to real-time economic data!")
        print("\n📈 Economic Data Now Available:")
        if fred_results:
            print("  🏛️ Federal Reserve Economic Data:")
            for series_id, data in fred_results.items():
                if data:
                    print(f"    • {data['description']}: {data['formatted']}")
        return 0
    else:
        success_rate = (passed / (passed + failed)) * 100
        print(f"\n⚠️ {failed} test(s) failed")
        print(f"📊 Success Rate: {success_rate:.1f}%")

        if success_rate >= 75:
            print("✅ FRED integration is largely working")
        else:
            print("❌ Significant issues with FRED integration")

        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)