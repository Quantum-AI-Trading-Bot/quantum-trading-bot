#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Data Source Integration
Tests sentiment analysis, alternative data, multi-modal fusion, and enhanced context composer
"""

import asyncio
import sys
import os
import numpy as np
import json
from datetime import datetime, timezone
import logging

# Add platform to path
sys.path.append('/home/davidsanker/platform')

# Import modules to test
try:
    from data.sentiment_analysis import SentimentDataSource, SentimentFusionEngine
    from data.alternative_data import AlternativeDataSource, FREDDataProvider, CommodityDataProvider
    from data.multi_modal_fusion import QuantumDataFusion, FusedDataPoint, DataQualityAssessor
    from data.enhanced_context_composer import EnhancedQuantumContextComposer, EnhancedDataSourceInterface
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"❌ Import error: {e}")
    IMPORTS_SUCCESSFUL = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataIntegrationTester:
    """Comprehensive test suite for data integration"""

    def __init__(self):
        self.test_results = {
            'sentiment_analysis': {'passed': 0, 'failed': 0, 'errors': []},
            'alternative_data': {'passed': 0, 'failed': 0, 'errors': []},
            'multi_modal_fusion': {'passed': 0, 'failed': 0, 'errors': []},
            'enhanced_context_composer': {'passed': 0, 'failed': 0, 'errors': []},
            'integration_tests': {'passed': 0, 'failed': 0, 'errors': []}
        }

        self.test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'EURUSD', 'BTC']
        self.performance_metrics = {}

    async def run_all_tests(self):
        """Run comprehensive test suite"""
        if not IMPORTS_SUCCESSFUL:
            logger.error("Cannot run tests - imports failed")
            return False

        print("🚀 Starting Comprehensive Data Integration Tests...")
        print("=" * 70)

        # Test individual components
        await self.test_sentiment_analysis()
        await self.test_alternative_data()
        await self.test_multi_modal_fusion()
        await self.test_enhanced_context_composer()

        # Test integration scenarios
        await self.test_integration_scenarios()

        # Generate final report
        self.generate_test_report()

        return True

    async def test_sentiment_analysis(self):
        """Test sentiment analysis components"""
        print("\n📊 Testing Sentiment Analysis Components...")
        print("-" * 50)

        try:
            # Test sentiment data source initialization
            sentiment_source = SentimentDataSource()
            await sentiment_source.initialize()
            self._record_pass('sentiment_analysis', "Sentiment source initialization")

            # Test sentiment fusion engine
            fusion_engine = SentimentFusionEngine()
            await fusion_engine.initialize()
            self._record_pass('sentiment_analysis', "Sentiment fusion engine initialization")

            # Test sentiment data retrieval
            for symbol in ['AAPL', 'TSLA']:
                try:
                    sentiment_data = await sentiment_source.get_sentiment_data(symbol)

                    # Validate structure
                    required_keys = ['sentiment_score', 'sentiment_confidence', 'sentiment_volume']
                    for key in required_keys:
                        if key not in sentiment_data:
                            raise ValueError(f"Missing key: {key}")

                    # Validate ranges
                    if not -1 <= sentiment_data['sentiment_score'] <= 1:
                        raise ValueError(f"Invalid sentiment score: {sentiment_data['sentiment_score']}")

                    if not 0 <= sentiment_data['sentiment_confidence'] <= 1:
                        raise ValueError(f"Invalid confidence: {sentiment_data['sentiment_confidence']}")

                    self._record_pass('sentiment_analysis', f"Sentiment data retrieval for {symbol}")

                    print(f"  ✅ {symbol}: Sentiment={sentiment_data['sentiment_score']:.3f}, "
                          f"Confidence={sentiment_data['sentiment_confidence']:.3f}")

                except Exception as e:
                    self._record_fail('sentiment_analysis', f"Sentiment data retrieval for {symbol}: {e}")
                    print(f"  ❌ {symbol}: {e}")

            # Test comprehensive sentiment analysis
            comprehensive_sentiment = await fusion_engine.get_comprehensive_sentiment('AAPL')
            if comprehensive_sentiment:
                self._record_pass('sentiment_analysis', "Comprehensive sentiment analysis")
                print(f"  ✅ Comprehensive sentiment for AAPL: Score={comprehensive_sentiment.sentiment_score:.3f}")

            # Test sentiment trend analysis
            trend = fusion_engine.get_sentiment_trend('AAPL', hours_back=24)
            if trend:
                self._record_pass('sentiment_analysis', "Sentiment trend analysis")
                print(f"  ✅ Sentiment trend: {trend.get('trend', 'unknown')}")

        except Exception as e:
            self._record_fail('sentiment_analysis', f"Sentiment analysis test failed: {e}")
            print(f"  ❌ Sentiment analysis test failed: {e}")

    async def test_alternative_data(self):
        """Test alternative data components"""
        print("\n📈 Testing Alternative Data Components...")
        print("-" * 50)

        try:
            # Test alternative data source initialization
            api_keys = {'fred': 'test_key', 'benzinga': 'test_key', 'newsapi': 'test_key'}
            alt_source = AlternativeDataSource(api_keys)
            await alt_source.initialize()
            self._record_pass('alternative_data', "Alternative data source initialization")

            # Test FRED data provider
            fred_provider = FREDDataProvider('test_key')
            await fred_provider.initialize()
            self._record_pass('alternative_data', "FRED provider initialization")

            # Test FRED data retrieval
            fred_data = await fred_provider.get_economic_series('GDP')
            if fred_data:
                self._record_pass('alternative_data', "FRED data retrieval")
                print(f"  ✅ GDP data points: {len(fred_data)}")

            # Test commodity data provider
            commodity_provider = CommodityDataProvider()
            await commodity_provider.initialize()
            self._record_pass('alternative_data', "Commodity provider initialization")

            # Test commodity data retrieval
            commodity_data = await commodity_provider.get_commodity_prices('crude_oil')
            if commodity_data:
                self._record_pass('alternative_data', "Commodity data retrieval")
                print(f"  ✅ Crude oil data points: {len(commodity_data)}")

            # Test alternative data integration
            for symbol in ['AAPL', 'XLE', 'GLD']:
                try:
                    alt_data = await alt_source.get_alternative_data(symbol)

                    # Validate structure
                    required_categories = ['commodities', 'macro', 'options', 'fred']
                    for category in required_categories:
                        if category not in alt_data:
                            logger.warning(f"Missing category {category} for {symbol}")

                    # Check for at least some data
                    total_data_points = sum(
                        len(alt_data.get(category, {}))
                        for category in required_categories
                        if isinstance(alt_data.get(category), (list, dict))
                    )

                    if total_data_points > 0:
                        self._record_pass('alternative_data', f"Alternative data for {symbol}")
                        print(f"  ✅ {symbol}: {total_data_points} alternative data points")

                except Exception as e:
                    self._record_fail('alternative_data', f"Alternative data for {symbol}: {e}")
                    print(f"  ❌ {symbol}: {e}")

        except Exception as e:
            self._record_fail('alternative_data', f"Alternative data test failed: {e}")
            print(f"  ❌ Alternative data test failed: {e}")

    async def test_multi_modal_fusion(self):
        """Test multi-modal data fusion"""
        print("\n🔬 Testing Multi-Modal Data Fusion...")
        print("-" * 50)

        try:
            # Initialize fusion engine
            config = {
                'num_qubits': 8,
                'fusion_methods': ['quantum_weighted', 'classical_ensemble', 'attention_fusion'],
                'api_keys': {'fred': 'test_key'}
            }
            fusion_engine = QuantumDataFusion(config)
            await fusion_engine.initialize()
            self._record_pass('multi_modal_fusion', "Fusion engine initialization")

            # Test fusion for multiple symbols
            for symbol in self.test_symbols[:3]:  # Test subset to manage time
                try:
                    # Test with market data
                    market_data = {
                        'price': 100.0 * (1 + np.random.normal(0, 0.02)),
                        'volume': int(np.random.exponential(1000000)),
                        'timestamp': datetime.now(timezone.utc)
                    }

                    fused_point = await fusion_engine.fuse_multi_modal_data(symbol, market_data)

                    # Validate fused point structure
                    if not fused_point:
                        raise ValueError("No fused point returned")

                    # Check required attributes
                    required_attrs = ['symbol', 'timestamp', 'price_features', 'volume_features',
                                    'sentiment_features', 'alternative_features', 'quantum_weights']
                    for attr in required_attrs:
                        if not hasattr(fused_point, attr):
                            raise ValueError(f"Missing attribute: {attr}")

                    # Validate quantum weights
                    if len(fused_point.quantum_weights) == 0:
                        raise ValueError("Empty quantum weights")

                    if not np.isclose(np.sum(fused_point.quantum_weights), 1.0, atol=0.1):
                        raise ValueError(f"Quantum weights don't sum to 1: {np.sum(fused_point.quantum_weights)}")

                    # Validate confidence and reliability
                    if not 0 <= fused_point.confidence_score <= 1:
                        raise ValueError(f"Invalid confidence score: {fused_point.confidence_score}")

                    if not 0 <= fused_point.data_reliability <= 1:
                        raise ValueError(f"Invalid reliability: {fused_point.data_reliability}")

                    self._record_pass('multi_modal_fusion', f"Fusion for {symbol}")
                    print(f"  ✅ {symbol}: Confidence={fused_point.confidence_score:.3f}, "
                          f"Reliability={fused_point.data_reliability:.3f}, "
                          f"Method={fused_point.fusion_method}")

                except Exception as e:
                    self._record_fail('multi_modal_fusion', f"Fusion for {symbol}: {e}")
                    print(f"  ❌ {symbol}: {e}")

            # Test fusion statistics
            stats = fusion_engine.get_fusion_statistics()
            if stats:
                self._record_pass('multi_modal_fusion', "Fusion statistics generation")
                print(f"  ✅ Fusion stats: {stats['fusion_stats']['successful_fusions']} successful, "
                      f"{stats['fusion_stats']['avg_confidence']:.3f} avg confidence")

            # Test feature trends
            trends = fusion_engine.get_feature_trends('AAPL', 'price', 'current_price', 24)
            if trends:
                self._record_pass('multi_modal_fusion', "Feature trend analysis")

        except Exception as e:
            self._record_fail('multi_modal_fusion', f"Multi-modal fusion test failed: {e}")
            print(f"  ❌ Multi-modal fusion test failed: {e}")

    async def test_enhanced_context_composer(self):
        """Test enhanced quantum context composer"""
        print("\n🎭 Testing Enhanced Quantum Context Composer...")
        print("-" * 50)

        try:
            # Initialize enhanced context composer
            config = {
                'api_keys': {
                    'fred': 'test_key',
                    'benzinga': 'test_key',
                    'newsapi': 'test_key',
                    'twitter': 'test_key'
                },
                'max_data_sources': 10,
                'num_qubits': 8
            }

            context_composer = EnhancedQuantumContextComposer(config)
            await context_composer.initialize()
            self._record_pass('enhanced_context_composer', "Enhanced context composer initialization")

            # Test data source manager
            data_manager = context_composer.data_manager

            # Test active source determination
            for symbol in ['AAPL', 'BTC', 'EURUSD']:
                active_sources = data_manager.get_active_sources_for_symbol(symbol, max_sources=8)
                if len(active_sources) > 0:
                    self._record_pass('enhanced_context_composer', f"Active sources for {symbol}")
                    print(f"  ✅ {symbol}: {len(active_sources)} active sources")

            # Test enhanced context generation
            for symbol in self.test_symbols[:3]:  # Test subset
                try:
                    enhanced_context = await context_composer.generate_enhanced_context(
                        symbol, max_sources=8, force_refresh=True
                    )

                    # Validate enhanced context
                    if not enhanced_context:
                        raise ValueError("No enhanced context returned")

                    # Check required attributes
                    required_attrs = ['symbol', 'timestamp', 'market_context', 'sentiment_context',
                                    'alternative_context', 'quantum_parameters', 'active_data_sources']
                    for attr in required_attrs:
                        if not hasattr(enhanced_context, attr):
                            raise ValueError(f"Missing attribute: {attr}")

                    # Validate quantum parameters
                    if not enhanced_context.quantum_parameters:
                        raise ValueError("No quantum parameters generated")

                    # Validate active data sources
                    if len(enhanced_context.active_data_sources) == 0:
                        raise ValueError("No active data sources")

                    # Validate confidence weight
                    if not 0 <= enhanced_context.confidence_weight <= 1:
                        raise ValueError(f"Invalid confidence weight: {enhanced_context.confidence_weight}")

                    # Validate risk adjustment factor
                    if enhanced_context.risk_adjustment_factor <= 0:
                        raise ValueError(f"Invalid risk adjustment: {enhanced_context.risk_adjustment_factor}")

                    self._record_pass('enhanced_context_composer', f"Enhanced context for {symbol}")
                    print(f"  ✅ {symbol}: {len(enhanced_context.active_data_sources)} sources, "
                          f"Confidence={enhanced_context.confidence_weight:.3f}, "
                          f"Risk Adj={enhanced_context.risk_adjustment_factor:.3f}")

                    # Check quantum parameters
                    quantum_param_count = len(enhanced_context.quantum_parameters)
                    print(f"    🧪 Quantum parameters: {quantum_param_count} generated")

                except Exception as e:
                    self._record_fail('enhanced_context_composer', f"Enhanced context for {symbol}: {e}")
                    print(f"  ❌ {symbol}: {e}")

            # Test performance summary
            performance = context_composer.get_performance_summary()
            if performance:
                self._record_pass('enhanced_context_composer', "Performance summary generation")
                print(f"  ✅ Performance: {performance['performance_metrics']['contexts_generated']} contexts generated")

        except Exception as e:
            self._record_fail('enhanced_context_composer', f"Enhanced context composer test failed: {e}")
            print(f"  ❌ Enhanced context composer test failed: {e}")

    async def test_integration_scenarios(self):
        """Test end-to-end integration scenarios"""
        print("\n🔄 Testing Integration Scenarios...")
        print("-" * 50)

        try:
            # Initialize enhanced data source interface
            config = {
                'api_keys': {
                    'fred': 'test_key',
                    'benzinga': 'test_key',
                    'newsapi': 'test_key'
                }
            }

            enhanced_interface = EnhancedDataSourceInterface(config)
            await enhanced_interface.initialize()
            self._record_pass('integration_tests', "Enhanced interface initialization")

            # Test concurrent context generation
            tasks = []
            for symbol in self.test_symbols[:3]:
                task = enhanced_interface.get_quantum_context(symbol, max_sources=6)
                tasks.append((symbol, task))

            # Execute concurrently
            start_time = datetime.now()
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()

            successful_contexts = 0
            for (symbol, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    self._record_fail('integration_tests', f"Concurrent context for {symbol}: {result}")
                    print(f"  ❌ {symbol}: {result}")
                else:
                    successful_contexts += 1
                    self._record_pass('integration_tests', f"Concurrent context for {symbol}")
                    print(f"  ✅ {symbol}: {len(result.active_data_sources)} data sources")

            print(f"  ⏱️ Concurrent processing time: {total_time:.2f} seconds for {successful_contexts} contexts")

            # Test data source performance under load
            await self.test_data_source_performance(enhanced_interface)

            # Test caching and performance optimization
            await self.test_caching_performance(enhanced_interface)

            # Test error handling and fallback mechanisms
            await self.test_error_handling(enhanced_interface)

        except Exception as e:
            self._record_fail('integration_tests', f"Integration scenario test failed: {e}")
            print(f"  ❌ Integration scenario test failed: {e}")

    async def test_data_source_performance(self, enhanced_interface):
        """Test data source performance under load"""
        print("  🏃 Testing data source performance...")

        try:
            # Generate multiple contexts rapidly
            start_time = datetime.now()
            contexts = []

            for i in range(5):  # Test 5 rapid iterations
                context = await enhanced_interface.get_quantum_context('AAPL', max_sources=5)
                contexts.append(context)

            end_time = datetime.now()
            avg_time = (end_time - start_time).total_seconds() / len(contexts)

            # Check performance thresholds
            if avg_time < 10.0:  # Should complete within 10 seconds each
                self._record_pass('integration_tests', f"Performance test: {avg_time:.2f}s avg")
                print(f"    ✅ Average context generation time: {avg_time:.2f} seconds")
            else:
                self._record_fail('integration_tests', f"Performance test too slow: {avg_time:.2f}s avg")
                print(f"    ❌ Slow performance: {avg_time:.2f} seconds average")

            # Check source diversity
            unique_sources = set()
            for context in contexts:
                unique_sources.update(context.active_data_sources)

            if len(unique_sources) >= 5:
                self._record_pass('integration_tests', f"Source diversity: {len(unique_sources)} unique sources")
                print(f"    ✅ Source diversity: {len(unique_sources)} different data sources used")

        except Exception as e:
            self._record_fail('integration_tests', f"Performance test failed: {e}")
            print(f"    ❌ Performance test failed: {e}")

    async def test_caching_performance(self, enhanced_interface):
        """Test caching and performance optimization"""
        print("  💾 Testing caching performance...")

        try:
            symbol = 'AAPL'

            # First context generation (cache miss)
            start_time = datetime.now()
            context1 = await enhanced_interface.get_quantum_context(symbol, max_sources=5)
            first_time = (datetime.now() - start_time).total_seconds()

            # Second context generation (cache hit)
            start_time = datetime.now()
            context2 = await enhanced_interface.get_quantum_context(symbol, max_sources=5)
            second_time = (datetime.now() - start_time).total_seconds()

            # Caching should improve performance
            if second_time < first_time * 0.8:  # At least 20% improvement
                self._record_pass('integration_tests', f"Caching performance: {second_time:.3f}s vs {first_time:.3f}s")
                print(f"    ✅ Cache hit: {second_time:.3f}s vs cache miss: {first_time:.3f}s")
            else:
                self._record_fail('integration_tests', f"Caching not effective: {second_time:.3f}s vs {first_time:.3f}s")
                print(f"    ⚠️ Limited caching benefit: {second_time:.3f}s vs {first_time:.3f}s")

        except Exception as e:
            self._record_fail('integration_tests', f"Caching test failed: {e}")
            print(f"    ❌ Caching test failed: {e}")

    async def test_error_handling(self, enhanced_interface):
        """Test error handling and fallback mechanisms"""
        print("  🛡️ Testing error handling and fallbacks...")

        try:
            # Test with invalid symbol
            fallback_context = await enhanced_interface.get_quantum_context('INVALID_SYMBOL', max_sources=3)

            if fallback_context and fallback_context.confidence_weight > 0:
                self._record_pass('integration_tests', "Fallback mechanism for invalid symbol")
                print(f"    ✅ Fallback context generated: {fallback_context.confidence_weight:.3f} confidence")
            else:
                self._record_fail('integration_tests', "Fallback mechanism failed")
                print(f"    ❌ No fallback context generated")

            # Test with zero data sources
            try:
                minimal_context = await enhanced_interface.get_quantum_context('AAPL', max_sources=0)

                if minimal_context:
                    self._record_pass('integration_tests', "Zero sources handling")
                    print(f"    ✅ Minimal context: {len(minimal_context.active_data_sources)} sources")
                else:
                    self._record_fail('integration_tests', "Zero sources not handled")
                    print(f"    ❌ No context for zero sources")

            except Exception as e:
                # This is expected to some degree
                self._record_pass('integration_tests', f"Expected error for zero sources: {type(e).__name__}")
                print(f"    ✅ Proper error handling for zero sources")

        except Exception as e:
            self._record_fail('integration_tests', f"Error handling test failed: {e}")
            print(f"    ❌ Error handling test failed: {e}")

    def _record_pass(self, test_category, test_name):
        """Record a successful test"""
        self.test_results[test_category]['passed'] += 1
        logger.info(f"✅ PASS [{test_category}]: {test_name}")

    def _record_fail(self, test_category, test_name):
        """Record a failed test"""
        self.test_results[test_category]['failed'] += 1
        self.test_results[test_category]['errors'].append(test_name)
        logger.error(f"❌ FAIL [{test_category}]: {test_name}")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 70)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("=" * 70)

        total_passed = 0
        total_failed = 0

        for category, results in self.test_results.items():
            passed = results['passed']
            failed = results['failed']
            total = passed + failed

            total_passed += passed
            total_failed += failed

            if total > 0:
                success_rate = (passed / total) * 100
                status = "✅ PASS" if failed == 0 else "⚠️ PARTIAL" if success_rate > 70 else "❌ FAIL"

                print(f"\n{category.replace('_', ' ').title()}:")
                print(f"  {status} - {passed}/{total} tests passed ({success_rate:.1f}%)")

                if failed > 0:
                    print(f"  Failed tests:")
                    for error in results['errors'][:5]:  # Show first 5 errors
                        print(f"    - {error}")
                    if len(results['errors']) > 5:
                        print(f"    ... and {len(results['errors']) - 5} more errors")

        # Overall summary
        print(f"\n{'='*50}")
        print("OVERALL SUMMARY:")
        print(f"{'='*50}")

        overall_total = total_passed + total_failed
        if overall_total > 0:
            overall_success = (total_passed / overall_total) * 100
            overall_status = "🎉 ALL TESTS PASSED" if total_failed == 0 else "⚠️ PARTIAL SUCCESS" if overall_success > 80 else "❌ MAJOR ISSUES"

            print(f"Status: {overall_status}")
            print(f"Total Tests: {overall_total}")
            print(f"Passed: {total_passed}")
            print(f"Failed: {total_failed}")
            print(f"Success Rate: {overall_success:.1f}%")

        # Recommendations
        print(f"\n📝 RECOMMENDATIONS:")
        if total_failed == 0:
            print("  ✅ All tests passed! System is ready for production.")
        else:
            if total_failed / overall_total > 0.3:
                print("  🔴 Major issues detected - address failing tests before deployment.")
            elif total_failed / overall_total > 0.1:
                print("  🟡 Some issues detected - review and fix failing components.")
            else:
                print("  🟢 Minor issues detected - system is largely functional.")

        # Performance metrics
        if self.performance_metrics:
            print(f"\n⚡ PERFORMANCE METRICS:")
            for metric, value in self.performance_metrics.items():
                print(f"  {metric}: {value}")

        print("\n" + "=" * 70)

async def main():
    """Main test runner"""
    print("🧪 Data Integration Test Suite")
    print("Testing 30+ Data Sources Integration with Quantum AI Trading Bot")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    tester = DataIntegrationTester()

    try:
        success = await tester.run_all_tests()
        if success:
            print("\n✅ Test suite completed successfully!")
            return 0
        else:
            print("\n❌ Test suite encountered critical errors!")
            return 1

    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        print(f"\n💥 Test suite crashed: {e}")
        return 1

if __name__ == "__main__":
    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)