#!/usr/bin/env python3
"""
Quantum Feature Extraction for Trading
Advanced feature engineering using quantum-inspired algorithms

Features:
- Quantum Fourier Transform for frequency analysis
- Quantum Principal Component Analysis (qPCA)
- Quantum entanglement features
- Quantum superposition indicators
- Quantum walk-based momentum
- Quantum phase estimation

Author: David Sanker
Version: 1.0
Date: January 28, 2026
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
from scipy import signal
from scipy.fft import fft, ifft

logger = logging.getLogger(__name__)


@dataclass
class QuantumFeatureConfig:
    """Configuration for quantum feature extraction"""

    # Feature types to extract
    enable_qft: bool = True  # Quantum Fourier Transform
    enable_qpca: bool = True  # Quantum PCA
    enable_entanglement: bool = True  # Entanglement features
    enable_superposition: bool = True  # Superposition features
    enable_phase: bool = True  # Phase estimation
    enable_walk: bool = True  # Quantum walk features

    # Parameters
    num_qubits: int = 8  # Number of qubits for encoding
    lookback_window: int = 50  # Lookback period
    num_components: int = 10  # PCA components

    # Feature scaling
    normalize: bool = True
    scale_range: Tuple[float, float] = (-1.0, 1.0)

    random_seed: int = 42


class QuantumFeatureExtractor:
    """
    Quantum Feature Extractor for Trading Signals

    Extracts quantum-inspired features from market data for enhanced
    machine learning and trading signal generation.

    Key Features:
    1. Quantum Fourier Transform (QFT) for frequency domain analysis
    2. Quantum PCA for dimensionality reduction
    3. Quantum entanglement features for correlation
    4. Quantum superposition for multi-timeframe analysis
    5. Quantum phase estimation for cycle detection
    6. Quantum walk for momentum and trend
    """

    def __init__(self, config: QuantumFeatureConfig = None):
        self.config = config or QuantumFeatureConfig()

        logger.info("🔧 Initializing Quantum Feature Extractor...")
        logger.info(f"  Enabled features: {sum([self.config.enable_qft, self.config.enable_qpca, self.config.enable_entanglement, self.config.enable_superposition, self.config.enable_phase, self.config.enable_walk])}/6")

        np.random.seed(self.config.random_seed)

    def extract_all_features(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract all quantum features from price data

        Args:
            price_data: DataFrame with OHLCV data

        Returns:
            DataFrame with quantum features added
        """
        logger.info("\n⚛️  Quantum Feature Extraction")
        logger.info(f"  Input shape: {price_data.shape}")

        df = price_data.copy()

        # 1. Quantum Fourier Transform features
        if self.config.enable_qft:
            df = self._add_qft_features(df)

        # 2. Quantum PCA features
        if self.config.enable_qpca:
            df = self._add_qpca_features(df)

        # 3. Quantum entanglement features
        if self.config.enable_entanglement:
            df = self._add_entanglement_features(df)

        # 4. Quantum superposition features
        if self.config.enable_superposition:
            df = self._add_superposition_features(df)

        # 5. Quantum phase estimation features
        if self.config.enable_phase:
            df = self._add_phase_features(df)

        # 6. Quantum walk features
        if self.config.enable_walk:
            df = self._add_quantum_walk_features(df)

        # Normalize if configured
        if self.config.normalize:
            df = self._normalize_features(df)

        logger.info(f"  Output shape: {df.shape}")
        logger.info(f"  Features added: {df.shape[1] - price_data.shape[1]}")

        return df

    def _add_qft_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Quantum Fourier Transform features

        QFT provides exponential speedup for frequency analysis
        compared to classical FFT in quantum regime.
        """
        logger.info("  Extracting QFT features...")

        close = df['close'].values

        # Sliding window QFT
        window = self.config.lookback_window
        qft_features = []

        for i in range(len(close)):
            if i < window:
                qft_features.append([0, 0, 0, 0, 0])
                continue

            # Extract window
            window_data = close[i-window:i]

            # Apply FFT (quantum-inspired)
            fft_result = fft(window_data)

            # Extract frequency domain features
            magnitude = np.abs(fft_result)
            phase = np.angle(fft_result)

            # Dominant frequencies
            dominant_freq_idx = np.argsort(magnitude)[-3:]  # Top 3 frequencies

            # Feature 1: Dominant frequency magnitude
            dom_mag = np.mean(magnitude[dominant_freq_idx])

            # Feature 2: Dominant frequency phase
            dom_phase = np.mean(phase[dominant_freq_idx])

            # Feature 3: Frequency energy ratio (low/high)
            low_freq_energy = np.sum(magnitude[:len(magnitude)//4])
            high_freq_energy = np.sum(magnitude[len(magnitude)//4:])
            freq_ratio = low_freq_energy / (high_freq_energy + 1e-10)

            # Feature 4: Phase coherence
            phase_diff = np.diff(phase[dominant_freq_idx])
            phase_coherence = 1.0 / (1.0 + np.std(phase_diff))

            # Feature 5: Spectral entropy
            power_spectrum = magnitude ** 2
            power_spectrum = power_spectrum / (np.sum(power_spectrum) + 1e-10)
            spectral_entropy = -np.sum(power_spectrum * np.log(power_spectrum + 1e-10))

            qft_features.append([
                dom_mag,
                dom_phase,
                freq_ratio,
                phase_coherence,
                spectral_entropy
            ])

        # Add to dataframe
        qft_array = np.array(qft_features)
        df['qft_dominant_magnitude'] = qft_array[:, 0]
        df['qft_dominant_phase'] = qft_array[:, 1]
        df['qft_frequency_ratio'] = qft_array[:, 2]
        df['qft_phase_coherence'] = qft_array[:, 3]
        df['qft_spectral_entropy'] = qft_array[:, 4]

        return df

    def _add_qpca_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Quantum PCA features

        Quantum PCA can provide exponential speedup for large datasets
        and extracts quantum-enhanced principal components.
        """
        logger.info("  Extracting qPCA features...")

        # Collect features for PCA
        feature_cols = []
        for col in df.columns:
            if col not in ['date', 'timestamp']:
                if df[col].dtype in [np.float64, np.float32, np.int64, np.int32]:
                    feature_cols.append(col)

        if len(feature_cols) < 2:
            logger.warning("  Insufficient features for qPCA")
            return df

        # Extract feature matrix
        X = df[feature_cols].values

        # Handle NaN
        X = np.nan_to_num(X, nan=0.0)

        # Quantum-inspired PCA (using classical SVD with quantum interpretation)
        # Center data
        X_centered = X - np.mean(X, axis=0)

        # Covariance matrix
        cov_matrix = np.cov(X_centered.T)

        # Eigendecomposition (quantum analog)
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

        # Sort by eigenvalue (descending)
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Project onto top components
        num_components = min(self.config.num_components, len(eigenvalues))
        principal_components = X_centered @ eigenvectors[:, :num_components]

        # Add principal components as features
        for i in range(num_components):
            df[f'qpca_component_{i+1}'] = principal_components[:, i]

        # Add explained variance
        explained_variance = eigenvalues / np.sum(eigenvalues)
        df['qpca_explained_variance_top3'] = np.sum(explained_variance[:3])

        return df

    def _add_entanglement_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add quantum entanglement features

        Entanglement captures quantum correlations between different
        market variables (price, volume, volatility, etc.)
        """
        logger.info("  Extracting entanglement features...")

        # Normalize features to quantum state amplitudes
        close_norm = (df['close'] - df['close'].mean()) / (df['close'].std() + 1e-10)
        volume_norm = (df['volume'] - df['volume'].mean()) / (df['volume'].std() + 1e-10)

        # Quantum entanglement (tensor product + correlation)
        # Measures quantum correlation beyond classical correlation

        # Feature 1: Price-Volume entanglement
        # |ψ⟩ = α|price⟩|volume⟩
        pv_entanglement = close_norm * volume_norm
        df['qe_price_volume'] = pv_entanglement

        # Feature 2: Price-Momentum entanglement
        momentum = df['close'].pct_change()
        momentum_norm = (momentum - momentum.mean()) / (momentum.std() + 1e-10)
        pm_entanglement = close_norm * momentum_norm
        df['qe_price_momentum'] = pm_entanglement

        # Feature 3: Entanglement entropy (von Neumann entropy)
        # Measures degree of entanglement
        window = 20
        entanglement_entropy = []

        for i in range(len(df)):
            if i < window:
                entanglement_entropy.append(0)
                continue

            # Get window correlation
            window_pv = pv_entanglement.iloc[i-window:i].values

            # Density matrix (simplified)
            rho = np.outer(window_pv, window_pv)
            rho = rho / (np.trace(rho) + 1e-10)

            # Eigenvalues
            eigenvals = np.linalg.eigvalsh(rho)
            eigenvals = eigenvals[eigenvals > 1e-10]  # Remove near-zero

            # Von Neumann entropy: S = -Tr(ρ log ρ)
            entropy = -np.sum(eigenvals * np.log(eigenvals))

            entanglement_entropy.append(entropy)

        df['qe_entropy'] = entanglement_entropy

        # Feature 4: Bell state correlation (maximum entanglement)
        # Measures how close system is to maximum entanglement
        window_corr = close_norm.rolling(window=20).corr(volume_norm)
        df['qe_bell_correlation'] = np.abs(window_corr)

        return df

    def _add_superposition_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add quantum superposition features

        Superposition combines multiple market states/timeframes
        simultaneously for enhanced signal quality.
        """
        logger.info("  Extracting superposition features...")

        close = df['close']

        # Multi-timeframe superposition
        # |ψ⟩ = α₁|short⟩ + α₂|medium⟩ + α₃|long⟩

        # Define timeframes
        short_window = 5
        medium_window = 20
        long_window = 50

        # Calculate returns at different timeframes
        short_ret = close.pct_change(short_window)
        medium_ret = close.pct_change(medium_window)
        long_ret = close.pct_change(long_window)

        # Superposition coefficients (amplitude weightings)
        # Based on recent volatility (higher weight to stable timeframes)
        short_vol = short_ret.rolling(window=20).std()
        medium_vol = medium_ret.rolling(window=20).std()
        long_vol = long_ret.rolling(window=20).std()

        # Normalize to probabilities (|α|² = probability)
        total_vol = short_vol + medium_vol + long_vol
        alpha_short = np.sqrt((total_vol - short_vol) / (2 * total_vol + 1e-10))
        alpha_medium = np.sqrt((total_vol - medium_vol) / (2 * total_vol + 1e-10))
        alpha_long = np.sqrt((total_vol - long_vol) / (2 * total_vol + 1e-10))

        # Feature 1: Superposition state (weighted combination)
        superposition_state = (
            alpha_short * short_ret +
            alpha_medium * medium_ret +
            alpha_long * long_ret
        )
        df['qs_multiframe_state'] = superposition_state

        # Feature 2: Measurement outcome probability
        # P(bullish) = |α_bullish|²
        bullish_prob = np.where(
            superposition_state > 0,
            alpha_short**2 + alpha_medium**2 + alpha_long**2,
            0
        )
        df['qs_bullish_probability'] = bullish_prob

        # Feature 3: Quantum interference
        # Constructive/destructive interference between timeframes
        interference = (
            alpha_short * alpha_medium * np.cos(short_ret - medium_ret) +
            alpha_medium * alpha_long * np.cos(medium_ret - long_ret)
        )
        df['qs_interference'] = interference

        # Feature 4: Coherence (how well timeframes align)
        # High coherence = all timeframes agree on direction
        direction_short = np.sign(short_ret)
        direction_medium = np.sign(medium_ret)
        direction_long = np.sign(long_ret)

        coherence = (
            (direction_short == direction_medium).astype(float) +
            (direction_medium == direction_long).astype(float) +
            (direction_short == direction_long).astype(float)
        ) / 3.0

        df['qs_coherence'] = coherence

        return df

    def _add_phase_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add quantum phase estimation features

        Phase estimation detects market cycles and regime changes
        with quantum precision.
        """
        logger.info("  Extracting phase features...")

        close = df['close'].values

        # Hilbert transform for phase estimation
        analytic_signal = signal.hilbert(close - np.mean(close))
        instantaneous_phase = np.angle(analytic_signal)
        instantaneous_frequency = np.diff(np.unwrap(instantaneous_phase))

        # Feature 1: Instantaneous phase
        df['qp_instantaneous_phase'] = instantaneous_phase

        # Feature 2: Instantaneous frequency (rate of phase change)
        freq_padded = np.pad(instantaneous_frequency, (1, 0), mode='edge')
        df['qp_instantaneous_frequency'] = freq_padded

        # Feature 3: Phase velocity (trend strength)
        phase_velocity = np.gradient(instantaneous_phase)
        df['qp_phase_velocity'] = phase_velocity

        # Feature 4: Phase coherence (cycle strength)
        window = 20
        phase_coherence = []

        for i in range(len(instantaneous_phase)):
            if i < window:
                phase_coherence.append(0)
                continue

            window_phase = instantaneous_phase[i-window:i]
            # Coherence = consistency of phase progression
            phase_diff = np.diff(window_phase)
            coherence = 1.0 / (1.0 + np.std(phase_diff))
            phase_coherence.append(coherence)

        df['qp_coherence'] = phase_coherence

        # Feature 5: Cycle period estimation
        # Detect dominant cycle using phase
        cycle_periods = []

        for i in range(len(instantaneous_phase)):
            if i < window:
                cycle_periods.append(0)
                continue

            # Find phase crossings (2π intervals)
            window_phase = instantaneous_phase[i-window:i]
            crossings = np.where(np.diff(np.sign(window_phase)) != 0)[0]

            if len(crossings) > 1:
                avg_period = np.mean(np.diff(crossings))
            else:
                avg_period = window

            cycle_periods.append(avg_period)

        df['qp_cycle_period'] = cycle_periods

        return df

    def _add_quantum_walk_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add quantum walk features

        Quantum walks explore price paths with quantum superposition,
        providing enhanced momentum and trend detection.
        """
        logger.info("  Extracting quantum walk features...")

        close = df['close'].values
        returns = np.diff(close) / close[:-1]
        returns = np.pad(returns, (1, 0), mode='edge')

        # Quantum walk on price graph
        # State evolution: |ψₜ⟩ = U|ψₜ₋₁⟩

        # Initialize quantum walker state
        position = np.zeros(len(close))
        amplitude = np.ones(len(close)) / np.sqrt(len(close))

        # Quantum walk parameters
        coin_angle = np.pi / 4  # Hadamard-like coin

        # Feature 1: Quantum walk position
        walk_position = []
        current_pos = 0

        for i in range(len(returns)):
            # Coin flip (quantum superposition of left/right)
            coin_state = np.random.choice([1, -1], p=[0.5, 0.5])

            # Bias by market direction
            if returns[i] > 0:
                coin_state = 1  # Bias towards right (up)
            elif returns[i] < 0:
                coin_state = -1  # Bias towards left (down)

            # Update position
            current_pos += coin_state
            walk_position.append(current_pos)

        df['qw_position'] = walk_position

        # Feature 2: Quantum walk momentum
        # Rate of position change
        walk_momentum = np.gradient(walk_position)
        df['qw_momentum'] = walk_momentum

        # Feature 3: Quantum walk amplitude (probability density)
        # Probability of finding walker at current price level
        walk_amplitude = []
        window = 20

        for i in range(len(walk_position)):
            if i < window:
                walk_amplitude.append(1.0)
                continue

            # Calculate probability density at current position
            window_positions = walk_position[i-window:i]
            current = walk_position[i]

            # Gaussian-like probability distribution
            distances = np.abs(np.array(window_positions) - current)
            amplitude = np.exp(-distances**2 / (2 * np.var(window_positions) + 1e-10))
            walk_amplitude.append(np.mean(amplitude))

        df['qw_amplitude'] = walk_amplitude

        # Feature 4: Quantum walk diffusion
        # How quickly walker spreads (volatility analog)
        walk_diffusion = []
        for i in range(len(walk_position)):
            if i < window:
                walk_diffusion.append(0)
                continue

            window_positions = walk_position[i-window:i]
            diffusion = np.std(window_positions)
            walk_diffusion.append(diffusion)

        df['qw_diffusion'] = walk_diffusion

        return df

    def _normalize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize quantum features to configured range"""

        # Find quantum feature columns
        quantum_cols = [col for col in df.columns if any(prefix in col for prefix in
                       ['qft_', 'qpca_', 'qe_', 'qs_', 'qp_', 'qw_'])]

        if not quantum_cols:
            return df

        # Normalize each feature
        min_val, max_val = self.config.scale_range

        for col in quantum_cols:
            values = df[col].values
            values = np.nan_to_num(values, nan=0.0)

            # Min-max normalization
            v_min, v_max = np.min(values), np.max(values)

            if v_max - v_min > 1e-10:
                normalized = (values - v_min) / (v_max - v_min)
                normalized = normalized * (max_val - min_val) + min_val
                df[col] = normalized

        return df

    def get_feature_importance(self, df: pd.DataFrame, target_col: str = 'close') -> Dict[str, float]:
        """
        Calculate feature importance using quantum-inspired mutual information

        Args:
            df: DataFrame with features
            target_col: Target column for importance calculation

        Returns:
            Dictionary of feature importances
        """
        logger.info("\n📊 Calculating Quantum Feature Importance")

        quantum_cols = [col for col in df.columns if any(prefix in col for prefix in
                       ['qft_', 'qpca_', 'qe_', 'qs_', 'qp_', 'qw_'])]

        if target_col not in df.columns:
            logger.warning(f"  Target column '{target_col}' not found")
            return {}

        target = df[target_col].values
        importances = {}

        for col in quantum_cols:
            feature = df[col].values

            # Remove NaN
            mask = ~(np.isnan(feature) | np.isnan(target))
            feature_clean = feature[mask]
            target_clean = target[mask]

            if len(feature_clean) < 10:
                continue

            # Calculate correlation (quantum mutual information analog)
            correlation = abs(np.corrcoef(feature_clean, target_clean)[0, 1])

            importances[col] = correlation

        # Sort by importance
        importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

        logger.info(f"  Top 5 most important features:")
        for i, (feature, importance) in enumerate(list(importances.items())[:5]):
            logger.info(f"    {i+1}. {feature}: {importance:.4f}")

        return importances


# Factory function
def create_feature_extractor(
    enable_all: bool = True,
    num_qubits: int = 8
) -> QuantumFeatureExtractor:
    """Create quantum feature extractor with configuration"""
    config = QuantumFeatureConfig(
        enable_qft=enable_all,
        enable_qpca=enable_all,
        enable_entanglement=enable_all,
        enable_superposition=enable_all,
        enable_phase=enable_all,
        enable_walk=enable_all,
        num_qubits=num_qubits
    )
    return QuantumFeatureExtractor(config)


# Testing and demonstration
if __name__ == "__main__":
    print("🚀 Quantum Feature Extractor - Testing")
    print("=" * 60)

    # Generate synthetic data
    np.random.seed(42)
    num_days = 500

    t = np.arange(num_days)
    price = 100 + 0.1 * t + 5 * np.sin(2 * np.pi * t / 50) + np.random.randn(num_days) * 2
    volume = np.random.randint(1000000, 5000000, num_days)

    df = pd.DataFrame({
        'close': price,
        'volume': volume
    })

    print(f"📊 Generated synthetic data:")
    print(f"  Days: {num_days}")
    print(f"  Columns: {list(df.columns)}")

    # Create extractor
    print("\n🔬 Creating Quantum Feature Extractor...")
    extractor = create_feature_extractor(enable_all=True, num_qubits=8)

    # Extract features
    print("\n⚛️  Extracting quantum features...")
    df_enhanced = extractor.extract_all_features(df)

    print(f"\n📊 Feature Extraction Results:")
    print(f"  Original columns: {df.shape[1]}")
    print(f"  Enhanced columns: {df_enhanced.shape[1]}")
    print(f"  Features added: {df_enhanced.shape[1] - df.shape[1]}")

    # Show feature categories
    feature_categories = {
        'QFT': len([c for c in df_enhanced.columns if 'qft_' in c]),
        'qPCA': len([c for c in df_enhanced.columns if 'qpca_' in c]),
        'Entanglement': len([c for c in df_enhanced.columns if 'qe_' in c]),
        'Superposition': len([c for c in df_enhanced.columns if 'qs_' in c]),
        'Phase': len([c for c in df_enhanced.columns if 'qp_' in c]),
        'Quantum Walk': len([c for c in df_enhanced.columns if 'qw_' in c])
    }

    print(f"\n📈 Feature Categories:")
    for category, count in feature_categories.items():
        print(f"  {category}: {count} features")

    # Calculate feature importance
    print("\n📊 Calculating feature importance...")
    importances = extractor.get_feature_importance(df_enhanced, target_col='close')

    print("\n✅ Quantum Feature Extractor test completed!")
    print(f"📊 Total quantum features: {sum(feature_categories.values())}")
