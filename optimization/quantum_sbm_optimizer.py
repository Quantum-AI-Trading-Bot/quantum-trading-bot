#!/usr/bin/env python3
"""
Quantum-Inspired Simulated Bifurcation Machine (SBM) Optimizer
Advanced quantum-inspired optimization engine for portfolio management and trading strategy optimization

Based on latest 2024-2025 research:
- Simulated Bifurcation for combinatorial optimization
- Quantum annealing-inspired algorithms
- Multi-objective portfolio optimization
- Ising model formulations for financial problems
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
from abc import ABC, abstractmethod
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)

@dataclass
class SBMConfig:
    """Configuration for Simulated Bifurcation Machine"""

    # Basic parameters
    num_variables: int = 100
    max_iterations: int = 1000
    convergence_threshold: float = 1e-6

    # SBM parameters
    alpha: float = 0.5  # Bifurcation parameter
    dt: float = 0.01    # Time step
    gamma: float = 0.9  # Damping coefficient
    k: float = 1.0      # Coupling strength

    # Optimization parameters
    population_size: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8

    # Quantum-inspired parameters
    quantum_probability: float = 0.1
    tunneling_rate: float = 0.05
    superposition_states: int = 3

    # Portfolio specific
    num_assets: int = 10
    risk_free_rate: float = 0.02
    target_return: float = 0.1
    max_weight: float = 0.3
    min_weight: float = 0.0

    # Multi-objective parameters
    num_objectives: int = 3  # Return, Risk, Sharpe
    objective_weights: List[float] = field(default_factory=lambda: [0.4, 0.3, 0.3])

    # Reproducibility
    seed: int = 42
    parallel: bool = True
    num_workers: int = 4

class IsingModel:
    """Ising model representation for optimization problems"""

    def __init__(self, num_spins: int, coupling_matrix: np.ndarray = None,
                 external_field: np.ndarray = None):
        self.num_spins = num_spins
        self.coupling_matrix = coupling_matrix if coupling_matrix is not None else np.zeros((num_spins, num_spins))
        self.external_field = external_field if external_field is not None else np.zeros(num_spins)

        # Ensure coupling matrix is symmetric
        self.coupling_matrix = (self.coupling_matrix + self.coupling_matrix.T) / 2

    def energy(self, spins: np.ndarray) -> float:
        """Calculate Ising model energy"""
        # Energy = -0.5 * sum(i,j) J_ij * s_i * s_j - sum(i) h_i * s_i
        interaction_energy = -0.5 * np.sum(self.coupling_matrix * np.outer(spins, spins))
        field_energy = -np.sum(self.external_field * spins)
        return interaction_energy + field_energy

    def local_field(self, spins: np.ndarray, spin_idx: int) -> float:
        """Calculate local field at spin index"""
        return np.sum(self.coupling_matrix[spin_idx] * spins) + self.external_field[spin_idx]

class SimulatedBifurcationMachine:
    """
    Simulated Bifurcation Machine for quantum-inspired optimization

    Based on the adiabatic bifurcation phenomenon in nonlinear dynamical systems
    that can efficiently solve combinatorial optimization problems.
    """

    def __init__(self, config: SBMConfig):
        self.config = config

        # Initialize SBM parameters
        self.positions = np.random.randn(config.num_variables)
        self.momenta = np.random.randn(config.num_variables) * 0.1

        # Time-dependent parameters
        self.time = 0.0
        self.alpha = config.alpha

        # Best solution tracking
        self.best_position = None
        self.best_energy = float('inf')
        self.energy_history = []

        logger.info(f"🚀 SBM Optimizer initialized:")
        logger.info(f"  Variables: {config.num_variables}")
        logger.info(f"  Max iterations: {config.max_iterations}")
        logger.info(f"  Population size: {config.population_size}")

    def update_alpha(self, iteration: int):
        """Update bifurcation parameter"""
        # Gradually increase alpha to induce bifurcation
        progress = iteration / self.config.max_iterations
        self.alpha = self.config.alpha * (1 + 10 * progress)

    def compute_forces(self, coupling_matrix: np.ndarray, external_field: np.ndarray) -> np.ndarray:
        """Compute forces from Ising model Hamiltonian"""
        forces = -coupling_matrix @ self.positions - external_field

        # Add nonlinear bifurcation terms
        nonlinear_forces = -self.alpha * self.positions * (1 - self.positions**2)
        forces += nonlinear_forces

        return forces

    def quantum_tunneling_step(self):
        """Apply quantum tunneling effect"""
        # Random jumps with probability proportional to quantum tunneling rate
        if np.random.random() < self.config.quantum_probability:
            tunneling_indices = np.random.choice(
                self.config.num_variables,
                size=max(1, int(self.config.num_variables * self.config.tunneling_rate)),
                replace=False
            )

            for idx in tunneling_indices:
                # Quantum jump to opposite value
                self.positions[idx] = -self.positions[idx]

    def superposition_evolution(self):
        """Evolve system in quantum superposition states"""
        if self.config.superposition_states > 1:
            # Create superposition of multiple states
            superposition_weight = 1.0 / self.config.superposition_states

            for _ in range(self.config.superposition_states - 1):
                # Generate perturbed state
                perturbation = np.random.randn(self.config.num_variables) * 0.1
                perturbed_state = self.positions + perturbation

                # Mix with current state
                self.positions = (1 - superposition_weight) * self.positions + superposition_weight * perturbed_state

    def step(self, coupling_matrix: np.ndarray, external_field: np.ndarray) -> float:
        """Single SBM optimization step"""
        # Compute forces
        forces = self.compute_forces(coupling_matrix, external_field)

        # Update positions (Verlet integration)
        self.positions += self.momenta * self.config.dt + 0.5 * forces * self.config.dt**2

        # Update momenta with damping
        new_forces = self.compute_forces(coupling_matrix, external_field)
        self.momenta = self.config.gamma * (self.momenta + 0.5 * (forces + new_forces) * self.config.dt)

        # Apply quantum effects
        self.quantum_tunneling_step()
        self.superposition_evolution()

        # Update time
        self.time += self.config.dt

        # Clip positions to [-1, 1] range (binary optimization)
        self.positions = np.clip(self.positions, -1, 1)

        # Calculate energy
        energy = -0.5 * np.sum(self.positions * forces)

        # Update best solution
        if energy < self.best_energy:
            self.best_energy = energy
            self.best_position = self.positions.copy()

        return energy

    def optimize(self, coupling_matrix: np.ndarray, external_field: np.ndarray) -> Tuple[np.ndarray, float]:
        """Run SBM optimization"""
        logger.info(f"🎯 Starting SBM optimization...")

        for iteration in range(self.config.max_iterations):
            # Update bifurcation parameter
            self.update_alpha(iteration)

            # Optimization step
            energy = self.step(coupling_matrix, external_field)
            self.energy_history.append(energy)

            # Check convergence
            if iteration > 100:
                recent_energies = self.energy_history[-100:]
                if np.std(recent_energies) < self.config.convergence_threshold:
                    logger.info(f"✅ Converged at iteration {iteration}")
                    break

            if iteration % 100 == 0:
                logger.info(f"Iteration {iteration}: Energy = {energy:.6f}, Alpha = {self.alpha:.3f}")

        # Convert best position to binary solution
        binary_solution = (self.best_position > 0).astype(int)

        logger.info(f"🏆 SBM optimization completed:")
        logger.info(f"  Best energy: {self.best_energy:.6f}")
        logger.info(f"  Final alpha: {self.alpha:.3f}")

        return binary_solution, self.best_energy

class PortfolioOptimizer:
    """Portfolio optimization using quantum-inspired SBM"""

    def __init__(self, config: SBMConfig):
        self.config = config
        self.sbm = SimulatedBifurcationMachine(config)

    def expected_return(self, weights: np.ndarray, returns: np.ndarray) -> float:
        """Calculate expected portfolio return"""
        return np.dot(weights, returns.mean(axis=0))

    def portfolio_risk(self, weights: np.ndarray, returns: np.ndarray) -> float:
        """Calculate portfolio risk (standard deviation)"""
        portfolio_returns = np.dot(returns, weights)
        return np.std(portfolio_returns)

    def sharpe_ratio(self, weights: np.ndarray, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        portfolio_return = self.expected_return(weights, returns)
        portfolio_risk = self.portfolio_risk(weights, returns)
        return (portfolio_return - risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0

    def value_at_risk(self, weights: np.ndarray, returns: np.ndarray, confidence: float = 0.95) -> float:
        """Calculate Value at Risk"""
        portfolio_returns = np.dot(returns, weights)
        return np.percentile(portfolio_returns, (1 - confidence) * 100)

    def build_ising_model(self, returns: np.ndarray, objective: str = 'sharpe') -> IsingModel:
        """Build Ising model for portfolio optimization"""
        num_assets = returns.shape[1]

        # Calculate covariance matrix and returns
        cov_matrix = np.cov(returns.T)
        expected_returns = np.mean(returns, axis=0)

        # Initialize Ising model
        ising = IsingModel(num_assets)

        if objective == 'sharpe':
            # Maximize Sharpe ratio
            for i in range(num_assets):
                for j in range(i+1, num_assets):
                    # Covariance penalty
                    ising.coupling_matrix[i, j] = cov_matrix[i, j] * self.config.k

                # Expected return benefit
                ising.external_field[i] = expected_returns[i] * self.config.k

        elif objective == 'risk_parity':
            # Minimize risk contribution
            for i in range(num_assets):
                for j in range(i+1, num_assets):
                    ising.coupling_matrix[i, j] = cov_matrix[i, j] * self.config.k

                # Risk parity constraint
                ising.external_field[i] = -1.0 / np.sqrt(cov_matrix[i, i]) * self.config.k

        elif objective == 'mean_variance':
            # Classic mean-variance optimization
            risk_aversion = 1.0
            for i in range(num_assets):
                for j in range(i+1, num_assets):
                    ising.coupling_matrix[i, j] = risk_aversion * cov_matrix[i, j] * self.config.k

                ising.external_field[i] = expected_returns[i] * self.config.k

        return ising

    def optimize_portfolio(self, returns: np.ndarray, objective: str = 'sharpe') -> Dict[str, Any]:
        """Optimize portfolio using SBM"""
        logger.info(f"🎯 Optimizing portfolio with {returns.shape[1]} assets")

        # Build Ising model
        ising_model = self.build_ising_model(returns, objective)

        # Run SBM optimization
        binary_weights, energy = self.sbm.optimize(ising_model.coupling_matrix, ising_model.external_field)

        # Convert binary to continuous weights
        continuous_weights = binary_weights.astype(float)

        # Apply constraints
        total_weight = np.sum(continuous_weights)
        if total_weight > 0:
            continuous_weights = continuous_weights / total_weight  # Normalize to sum to 1
        else:
            # If all weights are zero, use equal weights
            continuous_weights = np.ones(self.config.num_assets) / self.config.num_assets

        # Apply weight constraints
        continuous_weights = np.clip(continuous_weights, self.config.min_weight, self.config.max_weight)
        continuous_weights = continuous_weights / np.sum(continuous_weights)  # Re-normalize

        # Calculate portfolio metrics
        portfolio_return = self.expected_return(continuous_weights, returns)
        portfolio_risk = self.portfolio_risk(continuous_weights, returns)
        portfolio_sharpe = self.sharpe_ratio(continuous_weights, returns, self.config.risk_free_rate)
        portfolio_var = self.value_at_risk(continuous_weights, returns)

        results = {
            'weights': continuous_weights,
            'binary_weights': binary_weights,
            'expected_return': portfolio_return,
            'risk': portfolio_risk,
            'sharpe_ratio': portfolio_sharpe,
            'value_at_risk': portfolio_var,
            'energy': energy,
            'objective': objective,
            'convergence_history': self.sbm.energy_history
        }

        logger.info(f"✅ Portfolio optimization completed:")
        logger.info(f"  Expected return: {portfolio_return:.4f}")
        logger.info(f"  Risk: {portfolio_risk:.4f}")
        logger.info(f"  Sharpe ratio: {portfolio_sharpe:.4f}")
        logger.info(f"  VaR (95%): {portfolio_var:.4f}")

        return results

class MultiObjectiveOptimizer:
    """Multi-objective optimization using quantum-inspired methods"""

    def __init__(self, config: SBMConfig):
        self.config = config
        self.pareto_front = []

    def pareto_dominance(self, solution1: Dict, solution2: Dict) -> bool:
        """Check if solution1 dominates solution2"""
        objectives1 = [solution1['expected_return'], -solution1['risk'], solution1['sharpe_ratio']]
        objectives2 = [solution2['expected_return'], -solution2['risk'], solution2['sharpe_ratio']]

        better_in_any = False
        worse_in_any = False

        for obj1, obj2 in zip(objectives1, objectives2):
            if obj1 > obj2:
                better_in_any = True
            elif obj1 < obj2:
                worse_in_any = True

        return better_in_any and not worse_in_any

    def update_pareto_front(self, solution: Dict):
        """Update Pareto front with new solution"""
        # Remove dominated solutions
        self.pareto_front = [s for s in self.pareto_front if not self.pareto_dominance(solution, s)]

        # Add solution if not dominated by any existing solution
        if not any(self.pareto_dominance(s, solution) for s in self.pareto_front):
            self.pareto_front.append(solution)

    def optimize_multi_objective(self, returns: np.ndarray, num_solutions: int = 50) -> List[Dict]:
        """Run multi-objective optimization"""
        logger.info(f"🎯 Starting multi-objective optimization...")

        portfolio_optimizer = PortfolioOptimizer(self.config)

        # Define objectives with different weights
        objectives = [
            {'name': 'max_return', 'weights': [1.0, 0.0, 0.0]},
            {'name': 'min_risk', 'weights': [0.0, 1.0, 0.0]},
            {'name': 'max_sharpe', 'weights': [0.0, 0.0, 1.0]},
            {'name': 'balanced', 'weights': [0.33, 0.33, 0.34]},
            {'name': 'return_risk', 'weights': [0.6, 0.4, 0.0]},
        ]

        for _ in range(num_solutions):
            # Randomly select objective weighting
            objective = np.random.choice(objectives)['name']

            # Optimize portfolio
            solution = portfolio_optimizer.optimize_portfolio(returns, objective)

            # Update Pareto front
            self.update_pareto_front(solution)

        logger.info(f"✅ Multi-objective optimization completed:")
        logger.info(f"  Pareto front size: {len(self.pareto_front)} solutions")

        return self.pareto_front

class QuantumTradingStrategyOptimizer:
    """Complete quantum-inspired trading strategy optimization"""

    def __init__(self, config: SBMConfig):
        self.config = config
        self.portfolio_optimizer = PortfolioOptimizer(config)
        self.multi_objective_optimizer = MultiObjectiveOptimizer(config)

    def optimize_strategy(self, market_data: np.ndarray, returns: np.ndarray,
                          strategy_type: str = 'portfolio') -> Dict[str, Any]:
        """Optimize complete trading strategy"""
        logger.info(f"🚀 Starting quantum trading strategy optimization...")

        if strategy_type == 'portfolio':
            # Portfolio optimization
            result = self.portfolio_optimizer.optimize_portfolio(returns, 'sharpe')

        elif strategy_type == 'multi_objective':
            # Multi-objective optimization
            pareto_solutions = self.multi_objective_optimizer.optimize_multi_objective(returns)

            # Select best solution based on weighted objectives
            best_solution = None
            best_score = -float('inf')

            for solution in pareto_solutions:
                score = (self.config.objective_weights[0] * solution['expected_return'] +
                        self.config.objective_weights[1] * (1 - solution['risk']) +
                        self.config.objective_weights[2] * solution['sharpe_ratio'])

                if score > best_score:
                    best_score = score
                    best_solution = solution

            result = best_solution
            result['pareto_front'] = pareto_solutions
            result['pareto_front_size'] = len(pareto_solutions)

        elif strategy_type == 'adaptive':
            # Adaptive optimization with changing market conditions
            window_size = 60  # 60-day windows
            adaptive_results = []

            for i in range(0, len(returns) - window_size, window_size // 2):
                window_returns = returns[i:i+window_size]
                window_result = self.portfolio_optimizer.optimize_portfolio(window_returns, 'sharpe')
                window_result['window_start'] = i
                window_result['window_end'] = i + window_size
                adaptive_results.append(window_result)

            # Combine adaptive results
            avg_weights = np.mean([r['weights'] for r in adaptive_results], axis=0)
            avg_weights = avg_weights / np.sum(avg_weights)

            result = {
                'weights': avg_weights,
                'adaptive_results': adaptive_results,
                'strategy_type': 'adaptive'
            }

        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

        result['strategy_type'] = strategy_type
        result['optimization_time'] = datetime.now().isoformat()
        result['market_data_shape'] = market_data.shape
        result['returns_shape'] = returns.shape

        logger.info(f"✅ Trading strategy optimization completed:")
        logger.info(f"  Strategy type: {strategy_type}")
        logger.info(f"  Number of assets: {returns.shape[1]}")

        return result

    def backtest_strategy(self, result: Dict[str, Any], returns: np.ndarray,
                         transaction_costs: float = 0.001) -> Dict[str, Any]:
        """Backtest optimized strategy"""
        logger.info(f"📈 Backtesting strategy...")

        weights = result['weights']
        portfolio_returns = np.dot(returns, weights)

        # Apply transaction costs
        portfolio_returns -= transaction_costs

        # Calculate performance metrics
        cumulative_returns = np.cumprod(1 + portfolio_returns)
        total_return = cumulative_returns[-1] - 1

        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        volatility = np.std(portfolio_returns) * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0

        # Maximum drawdown
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = np.min(drawdown)

        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown < 0 else 0

        backtest_results = {
            'cumulative_returns': cumulative_returns.tolist(),
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio,
            'portfolio_returns': portfolio_returns.tolist(),
            'transaction_costs': transaction_costs
        }

        logger.info(f"✅ Backtest completed:")
        logger.info(f"  Total return: {total_return:.4f}")
        logger.info(f"  Annualized return: {annualized_return:.4f}")
        logger.info(f"  Volatility: {volatility:.4f}")
        logger.info(f"  Sharpe ratio: {sharpe_ratio:.4f}")
        logger.info(f"  Max drawdown: {max_drawdown:.4f}")

        return backtest_results

# Factory function
def create_quantum_optimizer(**kwargs) -> QuantumTradingStrategyOptimizer:
    """Create quantum trading strategy optimizer"""
    # Extract SBM-specific parameters
    sbm_params = {}
    for key, value in kwargs.items():
        if hasattr(SBMConfig(), key) or key in ['num_variables', 'num_assets', 'max_iterations',
                                                'population_size', 'alpha', 'dt', 'gamma', 'k']:
            sbm_params[key] = value

    config = SBMConfig(**sbm_params)

    return QuantumTradingStrategyOptimizer(config)

# Testing and demonstration
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    print("🚀 Quantum-Inspired SBM Optimizer - Testing")
    print("=" * 60)

    # Generate synthetic market data
    np.random.seed(42)
    num_assets = 10
    num_days = 252  # One trading year

    # Generate correlated returns
    correlation_matrix = np.random.randn(num_assets, num_assets) * 0.3
    correlation_matrix = correlation_matrix @ correlation_matrix.T
    correlation_matrix = correlation_matrix / np.max(correlation_matrix)
    np.fill_diagonal(correlation_matrix, 1)

    # Generate returns with given correlation
    chol = np.linalg.cholesky(correlation_matrix)
    random_returns = np.random.randn(num_days, num_assets) * 0.02  # 2% daily volatility
    returns = random_returns @ chol.T + 0.0001  # Small positive drift

    # Generate market features
    market_data = np.random.randn(num_days, 20)

    print(f"📊 Generated synthetic market data:")
    print(f"  Days: {num_days}")
    print(f"  Assets: {num_assets}")
    print(f"  Average daily return: {np.mean(returns):.4f}")
    print(f"  Average daily volatility: {np.std(returns):.4f}")

    # Create quantum optimizer
    optimizer = create_quantum_optimizer(
        num_assets=num_assets,
        max_iterations=500,
        population_size=30
    )

    print("\n🎯 Portfolio Optimization")
    portfolio_result = optimizer.optimize_strategy(market_data, returns, 'portfolio')

    print("\n🎯 Multi-Objective Optimization")
    multi_obj_result = optimizer.optimize_strategy(market_data, returns, 'multi_objective')

    print("\n📈 Backtesting Results")
    backtest_result = optimizer.backtest_strategy(portfolio_result, returns)

    # Plot results
    plt.figure(figsize=(15, 10))

    # Portfolio performance
    plt.subplot(2, 3, 1)
    cumulative_returns = backtest_result['cumulative_returns']
    plt.plot(cumulative_returns)
    plt.title('Portfolio Performance')
    plt.xlabel('Day')
    plt.ylabel('Cumulative Return')
    plt.grid(True)

    # Asset weights
    plt.subplot(2, 3, 2)
    weights = portfolio_result['weights']
    plt.bar(range(num_assets), weights)
    plt.title('Optimized Portfolio Weights')
    plt.xlabel('Asset')
    plt.ylabel('Weight')
    plt.grid(True)

    # Risk-return scatter
    plt.subplot(2, 3, 3)
    if 'pareto_front' in multi_obj_result:
        pareto_front = multi_obj_result['pareto_front']
        risks = [s['risk'] for s in pareto_front]
        returns = [s['expected_return'] for s in pareto_front]
        plt.scatter(risks, returns, alpha=0.6, label='Pareto Front')
        plt.scatter(portfolio_result['risk'], portfolio_result['expected_return'],
                   color='red', s=100, label='Selected Portfolio')
    plt.title('Risk-Return Trade-off')
    plt.xlabel('Risk')
    plt.ylabel('Expected Return')
    plt.legend()
    plt.grid(True)

    # Drawdown
    plt.subplot(2, 3, 4)
    portfolio_returns = np.array(backtest_result['portfolio_returns'])
    peak = np.maximum.accumulate(np.cumprod(1 + portfolio_returns))
    drawdown = (np.cumprod(1 + portfolio_returns) - peak) / peak
    plt.fill_between(range(len(drawdown)), drawdown, alpha=0.3, color='red')
    plt.title('Portfolio Drawdown')
    plt.xlabel('Day')
    plt.ylabel('Drawdown')
    plt.grid(True)

    # Convergence history
    plt.subplot(2, 3, 5)
    if 'convergence_history' in portfolio_result:
        convergence = portfolio_result['convergence_history']
        plt.plot(convergence)
        plt.title('SBM Convergence')
        plt.xlabel('Iteration')
        plt.ylabel('Energy')
        plt.grid(True)

    # Asset correlation matrix
    plt.subplot(2, 3, 6)
    im = plt.imshow(correlation_matrix, cmap='coolwarm', aspect='auto')
    plt.colorbar(im)
    plt.title('Asset Correlation Matrix')
    plt.xlabel('Asset')
    plt.ylabel('Asset')

    plt.tight_layout()
    plt.show()

    # Save results
    results = {
        'portfolio_optimization': portfolio_result,
        'multi_objective_optimization': multi_obj_result,
        'backtest_results': backtest_result,
        'configuration': optimizer.config.__dict__
    }

    with open('/home/davidsanker/platform/optimization/quantum_sbm_results.json', 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj

        json.dump(convert_numpy(results), f, indent=2)

    print("\n✅ Quantum SBM optimization completed successfully!")
    print(f"📊 Results saved to quantum_sbm_results.json")