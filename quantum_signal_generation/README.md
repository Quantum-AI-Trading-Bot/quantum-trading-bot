# Quantum Signal Generation - Quick Start Guide

## Overview

This module provides advanced quantum algorithms for trading signal generation, replacing classical technical analysis.

## Installation

```bash
cd /home/davidsanker/quantum-trading-bot-new
source /home/davidsanker/venv/bin/activate
pip install qiskit qiskit-aer qiskit-machine-learning pennylane matplotlib
```

## Usage

### Basic Usage (Single Symbol)

```python
from quantum_signal_generation.enhanced_quantum_analyzer import create_enhanced_quantum_analyzer
import yfinance as yf

# Create analyzer
analyzer = create_enhanced_quantum_analyzer()

# Get price data
ticker = yf.Ticker("AAPL")
data = ticker.history(period="6mo")
price_data = data['Close'].values

# Analyze
result = analyzer.analyze_market_quantum(
    symbol="AAPL",
    price_data=price_data,
    include_visualization=True
)

# Print results
print(f"Decision: {result['final_decision']['action']}")
print(f"Confidence: {result['final_decision']['confidence']:.1%}")
print(f"Quantum Score: {result['final_decision']['quantum_score']:.4f}")
```

### Batch Analysis (Multiple Symbols)

```python
from quantum_signal_generation.enhanced_quantum_analyzer import create_enhanced_quantum_analyzer
import yfinance as yf

# Create analyzer
analyzer = create_enhanced_quantum_analyzer()

# Define symbols
symbols = ["AAPL", "TSLA", "SPY", "QQQ", "IWM"]

# Fetch price data
price_data_dict = {}
for symbol in symbols:
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="6mo")
    price_data_dict[symbol] = data['Close'].values

# Batch analyze
results = analyzer.batch_analyze(symbols, price_data_dict)

# Print results
for symbol, result in results.items():
    if result:
        print(f"{symbol}: {result['final_decision']['action']} ({result['final_decision']['confidence']:.1%})")
```

### Export Analysis Report

```python
# Generate report
json_report = analyzer.export_analysis_report(
    analysis_result=result,
    output_path="/tmp/quantum_analysis_AAPL.json"
)
```

## Individual Algorithm Usage

### Quantum Fourier Transform (QFT) - Cycle Detection

```python
from quantum_signal_generation.quantum_fourier_analyzer import create_quantum_fourier_analyzer

# Create analyzer
qft_analyzer = create_quantum_fourier_analyzer(num_qubits=10)

# Detect cycles
cycle_analysis = qft_analyzer.detect_market_cycles(price_data)

# Print dominant cycles
for period, strength, phase in cycle_analysis['dominant_cycles']:
    print(f"Cycle: {period:.1f} days, Strength: {strength:.4f}")

# Generate signals
signals = qft_analyzer.generate_cycle_signals(cycle_analysis)
print(f"Buy Signal: {signals['buy_signal']:.4f}")
print(f"Sell Signal: {signals['sell_signal']:.4f}")
```

### Quantum Phase Estimation (QPE) - Trend Detection

```python
from quantum_signal_generation.quantum_trend_detector import create_quantum_trend_detector

# Create detector
qpe_detector = create_quantum_trend_detector(precision_qubits=5)

# Estimate trend phase
trend_analysis = qpe_detector.estimate_trend_phase(price_data)

# Print trend info
print(f"Direction: {trend_analysis['trend_direction']}")
print(f"Strength: {trend_analysis['trend_strength']:.2%}")
print(f"Confidence: {trend_analysis['confidence']:.2%}")

# Generate signals
signals = qpe_detector.generate_trend_signals(trend_analysis)
print(f"Trend Signal: {signals['trend_signal']:.4f}")
```

### Quantum Walk (QW) - Momentum Analysis

```python
from quantum_signal_generation.quantum_walk_momentum import create_quantum_walk_momentum

# Create analyzer
qw_analyzer = create_quantum_walk_momentum(num_positions=100)

# Analyze momentum
momentum_analysis = qw_analyzer.analyze_momentum(price_data)

# Print momentum info
print(f"Momentum: {momentum_analysis['momentum']:.4f}")
print(f"Diffusion Rate: {momentum_analysis['diffusion_rate']:.4f}")
print(f"Drift: {momentum_analysis['drift']:.4f}")

# Generate signals
signals = qw_analyzer.generate_momentum_signals(momentum_analysis)
print(f"Momentum Signal: {signals['momentum_signal']:.4f}")
```

## Output Format

### Complete Analysis Result

```python
{
    'symbol': 'AAPL',
    'timestamp': datetime(2026, 1, 28, 12, 0, 0),
    'data_points': 125,

    'cycle_analysis': {
        'dominant_cycles': [(20.1, 0.0125, 0.0), (50.0, 0.0080, 0.5)],
        'cycle_strength': 0.0251,
        'method': 'QUANTUM_QFT' or 'CLASSICAL_FFT_FALLBACK',
        'quantum_advantage': {'speedup_factor': 15.2}
    },

    'trend_analysis': {
        'direction': 'BULLISH',  # or 'BEARISH', 'NEUTRAL'
        'strength': 0.65,
        'confidence': 0.82,
        'method': 'QUANTUM_QPE' or 'CLASSICAL_FALLBACK',
        'quantum_advantage': {'speedup_factor': 10.0}
    },

    'momentum_analysis': {
        'momentum': 0.35,
        'diffusion_rate': 0.42,
        'method': 'QUANTUM_WALK' or 'CLASSICAL_RANDOM_WALK',
        'quantum_advantage': {'speedup_factor': 8.5}
    },

    'quantum_signals': {
        'buy_signal': 0.45,
        'sell_signal': 0.12,
        'overall_signal': 0.33,
        'strength': 0.57
    },

    'final_decision': {
        'action': 'BUY',  # or 'SELL', 'HOLD'
        'confidence': 0.78,
        'quantum_score': 0.33,
        'reasons': [
            'Quantum cycles aligned for upward movement',
            'Quantum phase estimation confirms bullish trend',
            'Quantum walk shows positive momentum buildup'
        ]
    },

    'analysis_method': 'ENHANCED_QUANTUM_V1',
    'quantum_utilization': 0.8  # 0.0 to 1.0 (80%)
}
```

## Configuration

### QFT Configuration

```python
from quantum_signal_generation.quantum_fourier_analyzer import QuantumFourierConfig

config = QuantumFourierConfig(
    num_qubits=10,           # Number of qubits (2^10 = 1024 states)
    shots=1000,              # Number of quantum measurements
    use_classical_fallback=True,  # Use FFT if Qiskit unavailable
    normalize_data=True,     # Normalize price to [-1, 1]
    detrend_data=True        # Remove linear trend
)
```

### QPE Configuration

```python
from quantum_signal_generation.quantum_trend_detector import QuantumTrendConfig

config = QuantumTrendConfig(
    precision_qubits=5,      # Precision of phase estimation
    num_qubits=3,            # Number of qubits for operator
    shots=1000,              # Number of measurements
    use_classical_fallback=True,
    momentum_window=20       # Window for momentum calculation
)
```

### QW Configuration

```python
from quantum_signal_generation.quantum_walk_momentum import QuantumWalkConfig

config = QuantumWalkConfig(
    num_positions=100,       # Number of positions in walk
    num_qubits=7,            # Number of qubits (2^7 = 128)
    num_steps=50,            # Number of walk steps
    shots=1000,              # Number of measurements
    use_classical_fallback=True,
    coin_type="hadamard"     # hadamard, grover, or fourier
)
```

## Performance Tips

1. **Use classical fallbacks during development**
   - Faster iteration without Qiskit
   - Easier debugging
   - Production-ready when Qiskit available

2. **Adjust num_qubits based on data size**
   - Small data (< 100 points): 8-10 qubits
   - Medium data (100-500 points): 10-12 qubits
   - Large data (> 500 points): 12-14 qubits

3. **Batch analysis for multiple symbols**
   - More efficient than individual calls
   - Reuses analyzer initialization

4. **Visualization during development**
   - Set `include_visualization=True`
   - Check /tmp/qft_spectrum_SYMBOL.png

## Troubleshooting

### Qiskit Import Errors

```python
WARNING:root:Qiskit not available - using classical FFT approximation
```

**Solution:**
```bash
pip install qiskit[all] qiskit-aer qiskit-machine-learning
```

### Weak Signals (All ~0.0)

**Problem:** All quantum scores near 0.0, decisions always HOLD

**Solutions:**
1. Check price data quality (need 50+ points)
2. Verify data is not all zeros or constant
3. Adjust signal combination weights
4. Lower BUY/SELL thresholds in `enhanced_quantum_analyzer.py`

### Matplotlib Missing

```python
WARNING:root:Matplotlib not available - skipping visualization
```

**Solution:**
```bash
pip install matplotlib
```

## Integration with Main Bot

Replace the `quantum_analyze()` function in `quantum_trading_bot.py`:

```python
# OLD (Classical Technical Analysis)
def quantum_analyze(self, symbol: str) -> Dict:
    # RSI, MACD, Bollinger Bands...
    quantum_score = sum(signals.values()) / len(signals)
    return {'action': action, 'confidence': confidence}

# NEW (Enhanced Quantum Analysis)
from quantum_signal_generation.enhanced_quantum_analyzer import create_enhanced_quantum_analyzer

def quantum_analyze(self, symbol: str) -> Dict:
    # Get price data
    data = self.get_market_data(symbol, period='6mo')

    # Use enhanced quantum analyzer
    analyzer = create_enhanced_quantum_analyzer()
    result = analyzer.analyze_market_quantum(
        symbol=symbol,
        price_data=data['close'].values
    )

    # Return decision
    return result['final_decision']
```

## Advanced Usage

### Custom Signal Weights

```python
analyzer = create_enhanced_quantum_analyzer()

# Adjust weights (default: 0.30 cycle, 0.40 trend, 0.30 momentum)
analyzer.signal_weights = {
    'cycle': 0.20,     # Less weight on cycles
    'trend': 0.50,     # More weight on trend
    'momentum': 0.30   # Same momentum weight
}
```

### Custom Decision Thresholds

Edit `enhanced_quantum_analyzer.py`:

```python
# In _generate_trading_decision() method
buy_threshold = 0.3     # Default: 0.3
sell_threshold = -0.3    # Default: -0.3
min_strength = 0.4       # Default: 0.4
```

## Testing

Run test suite:

```bash
cd quantum_signal_generation

# Test individual algorithms
python quantum_fourier_analyzer.py
python quantum_trend_detector.py
python quantum_walk_momentum.py

# Test enhanced analyzer
python enhanced_quantum_analyzer.py
```

## Support

For issues or questions:
1. Check logs: `grep "QUANTUM" /home/davidsanker/logs/*.log`
2. Review documentation: `/home/davidsanker/quantum_enhancement_roadmap.md`
3. Check build summary: `/home/davidsanker/PHASE1_QUANTUM_BUILD_SUMMARY.md`

## Version History

- **v1.0** (2026-01-28): Initial implementation
  - QFT for cycle detection
  - QPE for trend analysis
  - QW for momentum
  - Enhanced quantum analyzer

---

**Ready to quantum-enhance your trading! 🚀⚛️**
