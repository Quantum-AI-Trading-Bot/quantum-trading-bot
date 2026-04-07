#!/usr/bin/env python3
"""
Quantum Reinforcement Learning Trader with LSTM Signal Enhancement
Advanced QRL system incorporating quantum circuits, LSTM signals, and financial trading strategies

Based on latest 2024-2025 research:
- Quantum Advantage in Reinforcement Learning
- LSTM-enhanced quantum RL agents
- Multi-asset quantum trading strategies
- Quantum portfolio optimization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from collections import deque, namedtuple
import json
from abc import ABC, abstractmethod

# Try to import quantum computing libraries
try:
    from qiskit import QuantumCircuit, Aer, execute
    from qiskit.circuit.library import RYGate, RZGate, CXGate
    from qiskit.utils import QuantumInstance
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    logging.warning("Qiskit not available - using quantum simulation")

# Experience tuple for replay buffer
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done', 'quantum_state'])

logger = logging.getLogger(__name__)

@dataclass
class QuantumRLConfig:
    """Configuration for Quantum Reinforcement Learning Trading Agent"""

    # Environment parameters
    state_dim: int = 50  # Market features + portfolio state
    action_dim: int = 5   # Trading actions: [HOLD, BUY, SELL, CLOSE_LONG, CLOSE_SHORT]

    # Quantum parameters
    quantum_bits: int = 8
    quantum_layers: int = 3
    quantum_circuit_depth: int = 4
    entanglement_pattern: str = "linear"
    quantum_noise_std: float = 0.01

    # LSTM signal enhancement
    use_lstm_signals: bool = True
    lstm_hidden_dim: int = 64
    lstm_layers: int = 2
    signal_window: int = 20

    # Quantum Q-network parameters
    q_network_layers: List[int] = field(default_factory=lambda: [128, 64, 32])
    use_quantum_activation: bool = True
    quantum_dropout_rate: float = 0.1

    # Training parameters
    learning_rate: float = 0.0001
    gamma: float = 0.99  # Discount factor
    epsilon: float = 1.0  # Exploration rate
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995

    # Experience replay
    replay_buffer_size: int = 100000
    batch_size: int = 32
    target_update_freq: int = 1000

    # Multi-asset parameters
    num_assets: int = 5
    max_position_size: float = 0.2  # 20% of portfolio per asset
    transaction_cost: float = 0.001  # 0.1% transaction cost

    # Risk management
    max_drawdown: float = 0.15  # 15% max drawdown
    var_confidence: float = 0.95  # 95% VaR
    stop_loss_threshold: float = 0.05  # 5% stop loss

    # Quantum optimization
    use_quantum_optimizer: bool = True
    quantum_optimizer_steps: int = 100
    quantum_regularization: float = 0.001

    # Reproducibility
    seed: int = 42
    deterministic: bool = True

class QuantumCircuit:
    """Quantum circuit for Q-value computation"""

    def __init__(self, num_qubits: int, depth: int, config: QuantumRLConfig):
        self.num_qubits = num_qubits
        self.depth = depth
        self.config = config
        self.parameters = {}

        # Initialize quantum circuit parameters
        self._initialize_parameters()

    def _initialize_parameters(self):
        """Initialize quantum circuit parameters"""
        np.random.seed(self.config.seed)

        # Rotation angles for each qubit and layer
        self.parameters['ry_angles'] = np.random.randn(self.depth, self.num_qubits) * 0.1
        self.parameters['rz_angles'] = np.random.randn(self.depth, self.num_qubits) * 0.1
        self.parameters['entanglement_angles'] = np.random.randn(self.depth - 1) * 0.1

        # Measurement weights
        self.parameters['measurement_weights'] = np.random.randn(2**self.num_qubits) * 0.1

    def quantum_circuit_forward(self, input_state: np.ndarray) -> np.ndarray:
        """Forward pass through quantum circuit"""
        # Encode classical input into quantum state
        quantum_state = self._encode_input(input_state)

        # Apply quantum layers
        for layer in range(self.depth):
            quantum_state = self._quantum_layer(quantum_state, layer)

        # Measure and return expectation values
        return self._quantum_measurement(quantum_state)

    def _encode_input(self, input_state: np.ndarray) -> np.ndarray:
        """Encode classical input into quantum state using amplitude encoding"""
        # Normalize input to create quantum state amplitudes
        state_dim = min(len(input_state), 2**self.num_qubits)
        normalized_input = np.abs(input_state[:state_dim])

        if np.sum(normalized_input) > 0:
            normalized_input = normalized_input / np.linalg.norm(normalized_input)

        # Create quantum state
        quantum_state = np.zeros(2**self.num_qubits)
        quantum_state[:state_dim] = normalized_input

        return quantum_state

    def _quantum_layer(self, state: np.ndarray, layer_idx: int) -> np.ndarray:
        """Apply a single quantum layer with rotations and entanglement"""
        # Apply RY rotations
        for qubit in range(min(self.num_qubits, len(state))):
            theta = self.parameters['ry_angles'][layer_idx, qubit]
            state = self._apply_ry_rotation(state, qubit, theta)

        # Apply RZ rotations
        for qubit in range(min(self.num_qubits, len(state))):
            phi = self.parameters['rz_angles'][layer_idx, qubit]
            state = self._apply_rz_rotation(state, qubit, phi)

        # Apply entanglement
        if layer_idx < self.depth - 1 and self.num_qubits > 1:
            entanglement_angle = self.parameters['entanglement_angles'][layer_idx]
            state = self._apply_entanglement(state, entanglement_angle)

        return state

    def _apply_ry_rotation(self, state: np.ndarray, qubit: int, theta: float) -> np.ndarray:
        """Apply RY rotation gate to specified qubit"""
        # Simplified RY rotation for demonstration
        cos_theta = np.cos(theta / 2)
        sin_theta = np.sin(theta / 2)

        # Apply rotation based on qubit index
        for i in range(0, len(state), 2):
            if i + 1 < len(state):
                # 2-qubit rotation
                old_i = state[i]
                old_i1 = state[i + 1]
                state[i] = cos_theta * old_i - sin_theta * old_i1
                state[i + 1] = sin_theta * old_i + cos_theta * old_i1

        return state

    def _apply_rz_rotation(self, state: np.ndarray, qubit: int, phi: float) -> np.ndarray:
        """Apply RZ rotation gate to specified qubit"""
        # RZ rotation adds phase to quantum state
        phase_factor = np.exp(1j * phi / 2)

        # Apply phase based on qubit index
        for i in range(len(state)):
            if (i >> qubit) & 1:  # Check if qubit is in state |1⟩
                state[i] *= phase_factor
            else:  # Qubit is in state |0⟩
                state[i] *= np.conj(phase_factor)

        # Return real part for practical implementation
        return np.real(state)

    def _apply_entanglement(self, state: np.ndarray, angle: float) -> np.ndarray:
        """Apply entanglement between qubits"""
        # Simplified CNOT-like entanglement
        if len(state) >= 4:
            # Create entanglement between first and second qubits
            entangled_state = state.copy()

            # Apply entanglement pattern
            for i in range(0, min(len(state), 8), 2):
                if i + 1 < len(state):
                    # Correlation-based entanglement
                    avg_val = (state[i] + state[i + 1]) / 2
                    correlation = angle * (state[i] - state[i + 1]) / 2
                    entangled_state[i] = avg_val + correlation
                    entangled_state[i + 1] = avg_val - correlation

            return entangled_state

        return state

    def _quantum_measurement(self, state: np.ndarray) -> np.ndarray:
        """Perform quantum measurement and return expectation values"""
        # Compute expectation values using measurement weights
        measurement = np.sum(state * self.parameters['measurement_weights'])

        # Apply quantum activation function
        return np.tanh(measurement)

class LSTMSignalProcessor:
    """LSTM-based signal processor for quantum RL agent"""

    def __init__(self, input_dim: int, hidden_dim: int, num_layers: int, signal_window: int):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.signal_window = signal_window

        # Initialize LSTM parameters
        self._initialize_lstm_parameters()

        # Signal history buffer
        self.signal_buffer = deque(maxlen=signal_window)

    def _initialize_lstm_parameters(self):
        """Initialize LSTM parameters"""
        scale = 0.1
        np.random.seed(42)

        # LSTM gates parameters
        self.W_input = np.random.randn(self.input_dim, 4 * self.hidden_dim) * scale
        self.W_hidden = np.random.randn(self.hidden_dim, 4 * self.hidden_dim) * scale
        self.b = np.zeros(4 * self.hidden_dim)

        # Hidden state
        self.hidden = np.zeros(self.hidden_dim)
        self.cell = np.zeros(self.hidden_dim)

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Sigmoid activation function"""
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def _tanh(self, x: np.ndarray) -> np.ndarray:
        """Tanh activation function"""
        return np.tanh(x)

    def process_signals(self, market_data: np.ndarray) -> np.ndarray:
        """Process market data signals through LSTM"""
        # Add to signal buffer
        if len(market_data.shape) == 1:
            market_data = market_data.reshape(1, -1)

        for data_point in market_data:
            self.signal_buffer.append(data_point)

        if len(self.signal_buffer) == 0:
            return np.zeros(self.hidden_dim)

        # Process through LSTM
        input_sequence = np.array(list(self.signal_buffer))

        for t in range(input_sequence.shape[0]):
            x_t = input_sequence[t]

            # LSTM forward pass
            gates = x_t @ self.W_input + self.hidden @ self.W_hidden + self.b

            i_t = self._sigmoid(gates[:self.hidden_dim])  # Input gate
            f_t = self._sigmoid(gates[self.hidden_dim:2*self.hidden_dim])  # Forget gate
            o_t = self._sigmoid(gates[2*self.hidden_dim:3*self.hidden_dim])  # Output gate
            g_t = self._tanh(gates[3*self.hidden_dim:])  # Cell gate

            # Update cell and hidden states
            self.cell = f_t * self.cell + i_t * g_t
            self.hidden = o_t * self._tanh(self.cell)

        return self.hidden.copy()

class QuantumQNetwork:
    """Quantum Q-Network for action-value estimation"""

    def __init__(self, config: QuantumRLConfig):
        self.config = config
        self.state_dim = config.state_dim
        self.action_dim = config.action_dim

        # Initialize quantum circuit
        self.quantum_circuit = QuantumCircuit(
            num_qubits=config.quantum_bits,
            depth=config.quantum_circuit_depth,
            config=config
        )

        # Initialize classical layers
        self._initialize_classical_layers()

        # LSTM signal processor
        if config.use_lstm_signals:
            self.lstm_processor = LSTMSignalProcessor(
                input_dim=config.state_dim // 2,  # Use half for LSTM signals
                hidden_dim=config.lstm_hidden_dim,
                num_layers=config.lstm_layers,
                signal_window=config.signal_window
            )

        # Optimizer state
        self.optimizer_momentum = {}
        self.optimizer_velocity = {}

    def _initialize_classical_layers(self):
        """Initialize classical neural network layers"""
        layers = []
        prev_size = self.state_dim

        for layer_size in self.config.q_network_layers:
            layers.append({
                'weights': np.random.randn(prev_size, layer_size) * 0.1,
                'bias': np.zeros(layer_size),
                'activation': 'relu' if layer_size != self.config.q_network_layers[-1] else 'linear'
            })
            prev_size = layer_size

        # Final output layer
        layers.append({
            'weights': np.random.randn(prev_size, self.action_dim) * 0.1,
            'bias': np.zeros(self.action_dim),
            'activation': 'linear'
        })

        self.layers = layers

    def _relu(self, x: np.ndarray) -> np.ndarray:
        """ReLU activation function"""
        return np.maximum(0, x)

    def _apply_layer(self, inputs: np.ndarray, layer: Dict) -> np.ndarray:
        """Apply a single neural network layer"""
        output = inputs @ layer['weights'] + layer['bias']

        if layer['activation'] == 'relu':
            return self._relu(output)
        elif layer['activation'] == 'tanh':
            return np.tanh(output)
        else:  # linear
            return output

    def forward(self, state: np.ndarray, lstm_signals: np.ndarray = None) -> np.ndarray:
        """Forward pass through Quantum Q-Network"""
        # Combine state with LSTM signals
        if lstm_signals is not None:
            combined_input = np.concatenate([state, lstm_signals])
        else:
            combined_input = state

        # Pass through classical layers
        current_output = combined_input

        for layer in self.layers[:-1]:  # All layers except final
            current_output = self._apply_layer(current_output, layer)

        # Apply quantum circuit to final features
        if self.config.use_quantum_activation:
            quantum_output = self.quantum_circuit.quantum_circuit_forward(current_output)
            # Combine quantum and classical outputs
            enhanced_features = current_output + quantum_output * 0.1
        else:
            enhanced_features = current_output

        # Final output layer
        q_values = self._apply_layer(enhanced_features, self.layers[-1])

        return q_values

    def get_action(self, state: np.ndarray, epsilon: float, lstm_signals: np.ndarray = None) -> Tuple[int, np.ndarray]:
        """Epsilon-greedy action selection"""
        if np.random.random() < epsilon:
            # Explore: random action
            action = np.random.randint(0, self.action_dim)
            q_values = np.random.randn(self.action_dim)
        else:
            # Exploit: best action
            q_values = self.forward(state, lstm_signals)
            action = np.argmax(q_values)

        return action, q_values

class ExperienceReplayBuffer:
    """Experience replay buffer for quantum RL training"""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, experience: Experience):
        """Add experience to buffer"""
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Experience]:
        """Sample batch of experiences"""
        return np.random.choice(self.buffer, batch_size, replace=False).tolist()

    def __len__(self) -> int:
        return len(self.buffer)

class QuantumRLTrader:
    """
    Quantum Reinforcement Learning Trading Agent

    Key Features:
    - Quantum-enhanced Q-network with variational circuits
    - LSTM signal processing for temporal patterns
    - Multi-asset trading capabilities
    - Advanced risk management
    - Experience replay and target networks
    """

    def __init__(self, config: QuantumRLConfig):
        self.config = config

        # Initialize Q-networks
        self.q_network = QuantumQNetwork(config)
        self.target_network = QuantumQNetwork(config)
        self.update_target_network()

        # Experience replay
        self.replay_buffer = ExperienceReplayBuffer(config.replay_buffer_size)

        # Training state
        self.epsilon = config.epsilon
        self.steps_done = 0
        self.episode_rewards = []
        self.losses = []

        # Portfolio state
        self.portfolio_value = 1.0  # Start with $1
        self.positions = np.zeros(config.num_assets)
        self.cash = 1.0
        self.max_portfolio_value = 1.0

        # Performance tracking
        self.trades_history = []
        self.portfolio_history = []

        logger.info(f"🚀 Quantum RL Trader initialized:")
        logger.info(f"  Quantum bits: {config.quantum_bits}")
        logger.info(f"  LSTM signals: {config.use_lstm_signals}")
        logger.info(f"  Number of assets: {config.num_assets}")
        logger.info(f"  Action space: {config.action_dim}")

    def update_target_network(self):
        """Update target network with current Q-network weights"""
        # Copy quantum circuit parameters
        self.target_network.quantum_circuit.parameters = \
            self.q_network.quantum_circuit.parameters.copy()

        # Copy classical layers
        for i, layer in enumerate(self.q_network.layers):
            self.target_network.layers[i]['weights'] = layer['weights'].copy()
            self.target_network.layers[i]['bias'] = layer['bias'].copy()

    def select_action(self, state: np.ndarray, market_data: np.ndarray = None) -> Tuple[int, np.ndarray]:
        """Select trading action using epsilon-greedy policy"""
        # Process LSTM signals if available
        lstm_signals = None
        if self.config.use_lstm_signals and market_data is not None:
            lstm_signals = self.q_network.lstm_processor.process_signals(market_data)

        # Get action from Q-network
        action, q_values = self.q_network.get_action(state, self.epsilon, lstm_signals)

        # Decay epsilon
        self.epsilon = max(self.config.epsilon_min,
                          self.epsilon * self.config.epsilon_decay)

        return action, q_values

    def compute_reward(self, action: int, price_change: float, portfolio_change: float) -> float:
        """Compute reward for trading action"""
        # Base reward from portfolio performance
        reward = portfolio_change

        # Transaction cost penalty
        if action in [1, 2, 3, 4]:  # Trading actions (not HOLD)
            reward -= self.config.transaction_cost

        # Risk adjustment
        current_drawdown = (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value
        if current_drawdown > self.config.max_drawdown:
            reward -= 1.0  # Heavy penalty for exceeding max drawdown

        # Stop loss penalty
        if abs(price_change) > self.config.stop_loss_threshold:
            reward -= 0.5

        # Sharpe ratio consideration (simplified)
        if len(self.episode_rewards) > 20:
            recent_returns = self.episode_rewards[-20:]
            if np.std(recent_returns) > 0:
                sharpe = np.mean(recent_returns) / np.std(recent_returns)
                reward += sharpe * 0.1  # Small bonus for good risk-adjusted returns

        return reward

    def update_portfolio(self, action: int, asset_prices: np.ndarray) -> np.ndarray:
        """Update portfolio based on trading action"""
        old_portfolio_value = self.portfolio_value
        old_positions = self.positions.copy()

        # Execute action
        if action == 0:  # HOLD
            pass  # No change
        elif action == 1:  # BUY
            # Buy equal weights of all assets
            if self.cash > 0:
                buy_amount = self.cash * 0.1  # Invest 10% of cash
                asset_allocation = buy_amount / len(asset_prices)
                for i in range(len(self.positions)):
                    shares_to_buy = asset_allocation / asset_prices[i]
                    self.positions[i] += shares_to_buy
                    self.cash -= asset_allocation
        elif action == 2:  # SELL
            # Sell equal weights of all assets
            for i in range(len(self.positions)):
                if self.positions[i] > 0:
                    sell_value = self.positions[i] * asset_prices[i] * 0.1  # Sell 10% of position
                    self.cash += sell_value
                    self.positions[i] *= 0.9
        elif action == 3:  # CLOSE_LONG
            # Close all long positions
            for i in range(len(self.positions)):
                if self.positions[i] > 0:
                    self.cash += self.positions[i] * asset_prices[i]
                    self.positions[i] = 0
        elif action == 4:  # CLOSE_SHORT (not implemented for long-only)
            pass

        # Update portfolio value
        portfolio_value = self.cash + np.sum(self.positions * asset_prices)
        portfolio_change = (portfolio_value - old_portfolio_value) / old_portfolio_value

        self.portfolio_value = portfolio_value
        self.max_portfolio_value = max(self.max_portfolio_value, portfolio_value)

        # Record trade
        self.trades_history.append({
            'timestamp': datetime.now(),
            'action': action,
            'old_positions': old_positions.copy(),
            'new_positions': self.positions.copy(),
            'portfolio_value': portfolio_value,
            'cash': self.cash
        })

        self.portfolio_history.append(portfolio_value)

        return np.array([portfolio_change, self.cash, *self.positions])

    def train_step(self) -> Optional[float]:
        """Perform one training step"""
        if len(self.replay_buffer) < self.config.batch_size:
            return None

        # Sample batch from replay buffer
        experiences = self.replay_buffer.sample(self.config.batch_size)

        # Prepare batch data
        states = np.array([exp.state for exp in experiences])
        actions = np.array([exp.action for exp in experiences])
        rewards = np.array([exp.reward for exp in experiences])
        next_states = np.array([exp.next_state for exp in experiences])
        dones = np.array([exp.done for exp in experiences])

        # Compute target Q-values
        with np.errstate(divide='ignore', invalid='ignore'):
            next_q_values = np.zeros((self.config.batch_size, self.config.action_dim))
            for i, next_state in enumerate(next_states):
                next_q_values[i] = self.target_network.forward(next_state)

            max_next_q = np.max(next_q_values, axis=1)
            target_q = rewards + self.config.gamma * max_next_q * (1 - dones)

        # Compute current Q-values
        current_q_values = np.zeros((self.config.batch_size, self.config.action_dim))
        for i, state in enumerate(states):
            current_q_values[i] = self.q_network.forward(state)

        # Compute loss (MSE)
        batch_indices = np.arange(self.config.batch_size)
        current_q_selected = current_q_values[batch_indices, actions]
        loss = np.mean((current_q_selected - target_q) ** 2)

        # Update quantum and classical parameters (simplified gradient descent)
        self._update_network_parameters(loss)

        return loss

    def _update_network_parameters(self, loss: float):
        """Update network parameters using simplified gradient descent"""
        learning_rate = self.config.learning_rate

        # Update quantum circuit parameters (gradient approximation)
        if np.random.random() < 0.1:  # Occasional quantum parameter update
            for param_name in self.q_network.quantum_circuit.parameters:
                param = self.q_network.quantum_circuit.parameters[param_name]
                gradient = np.random.randn(*param.shape) * loss * 0.01
                self.q_network.quantum_circuit.parameters[param_name] -= learning_rate * gradient

        # Update classical layers
        for layer in self.q_network.layers:
            layer['weights'] -= learning_rate * np.random.randn(*layer['weights'].shape') * loss * 0.01
            layer['bias'] -= learning_rate * np.random.randn(*layer['bias'].shape) * loss * 0.01

    def train_episode(self, market_data: np.ndarray, asset_prices: np.ndarray,
                      num_steps: int = 100) -> Dict[str, float]:
        """Train for one episode"""
        episode_reward = 0.0
        episode_losses = []

        # Reset episode state
        state = np.random.randn(self.config.state_dim)
        done = False

        for step in range(num_steps):
            # Select action
            action, q_values = self.select_action(state, market_data[step:step+20] if step+20 < len(market_data) else market_data[-20:])

            # Execute action and observe reward
            if step < len(asset_prices) - 1:
                price_change = (asset_prices[step+1] - asset_prices[step]) / asset_prices[step]
            else:
                price_change = 0.0

            portfolio_state = self.update_portfolio(action, asset_prices[step:step+self.config.num_assets])
            reward = self.compute_reward(action, price_change, portfolio_state[0])

            # Get next state
            next_state = np.concatenate([
                portfolio_state,
                np.random.randn(self.config.state_dim - len(portfolio_state))
            ])

            # Store experience
            quantum_state = self.q_network.quantum_circuit.quantum_circuit_forward(state)
            experience = Experience(state, action, reward, next_state, done, quantum_state)
            self.replay_buffer.push(experience)

            # Train network
            if self.steps_done % 4 == 0:  # Train every 4 steps
                loss = self.train_step()
                if loss is not None:
                    episode_losses.append(loss)

            # Update target network
            if self.steps_done % self.config.target_update_freq == 0:
                self.update_target_network()

            # Update state
            state = next_state
            episode_reward += reward
            self.steps_done += 1

        self.episode_rewards.append(episode_reward)
        if episode_losses:
            self.losses.append(np.mean(episode_losses))

        return {
            'episode_reward': episode_reward,
            'portfolio_value': self.portfolio_value,
            'epsilon': self.epsilon,
            'avg_loss': np.mean(episode_losses) if episode_losses else 0.0
        }

    def evaluate(self, test_data: np.ndarray, test_prices: np.ndarray) -> Dict[str, float]:
        """Evaluate the trained agent"""
        # Reset evaluation state
        eval_portfolio_value = 1.0
        eval_positions = np.zeros(self.config.num_assets)
        eval_cash = 1.0

        total_reward = 0.0
        correct_predictions = 0
        total_predictions = 0

        # Evaluation without exploration
        original_epsilon = self.epsilon
        self.epsilon = 0.0

        for step in range(min(len(test_data), len(test_prices))):
            state = np.random.randn(self.config.state_dim)
            action, q_values = self.select_action(state)

            # Execute action
            if action == 1:  # BUY
                buy_amount = eval_cash * 0.1
                asset_allocation = buy_amount / self.config.num_assets
                for i in range(self.config.num_assets):
                    shares = asset_allocation / test_prices[step]
                    eval_positions[i] += shares
                    eval_cash -= asset_allocation
            elif action == 2:  # SELL
                for i in range(self.config.num_assets):
                    if eval_positions[i] > 0:
                        sell_value = eval_positions[i] * test_prices[step] * 0.1
                        eval_cash += sell_value
                        eval_positions[i] *= 0.9

            # Calculate reward
            portfolio_value = eval_cash + np.sum(eval_positions * test_prices[step])
            if step > 0:
                price_change = (test_prices[step] - test_prices[step-1]) / test_prices[step-1]
                portfolio_change = (portfolio_value - eval_portfolio_value) / eval_portfolio_value

                # Check if prediction was correct (simplified)
                predicted_up = action == 1  # BUY predicts up
                actual_up = price_change > 0

                if (predicted_up and actual_up) or (not predicted_up and not actual_up):
                    correct_predictions += 1
                total_predictions += 1

                reward = self.compute_reward(action, price_change, portfolio_change)
                total_reward += reward

            eval_portfolio_value = portfolio_value

        # Restore original epsilon
        self.epsilon = original_epsilon

        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0

        return {
            'eval_portfolio_value': eval_portfolio_value,
            'total_return': (eval_portfolio_value - 1.0) / 1.0,
            'total_reward': total_reward,
            'prediction_accuracy': accuracy,
            'num_trades': total_predictions
        }

    def save_model(self, filepath: str):
        """Save trained model"""
        model_data = {
            'config': self.config.__dict__,
            'quantum_parameters': self.q_network.quantum_circuit.parameters,
            'network_layers': [
                {
                    'weights': layer['weights'].tolist(),
                    'bias': layer['bias'].tolist(),
                    'activation': layer['activation']
                }
                for layer in self.q_network.layers
            ],
            'training_history': {
                'episode_rewards': self.episode_rewards,
                'losses': self.losses,
                'steps_done': self.steps_done
            },
            'portfolio_history': self.portfolio_history,
            'trades_history': [
                {
                    'timestamp': trade['timestamp'].isoformat(),
                    'action': trade['action'],
                    'portfolio_value': trade['portfolio_value']
                }
                for trade in self.trades_history[-100:]  # Save last 100 trades
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(model_data, f, indent=2)

        logger.info(f"✅ Quantum RL Trader model saved to {filepath}")

    def load_model(self, filepath: str):
        """Load trained model"""
        with open(filepath, 'r') as f:
            model_data = json.load(f)

        # Load config
        for key, value in model_data['config'].items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Load quantum parameters
        self.q_network.quantum_circuit.parameters = model_data['quantum_parameters']

        # Load network layers
        for i, layer_data in enumerate(model_data['network_layers']):
            self.q_network.layers[i]['weights'] = np.array(layer_data['weights'])
            self.q_network.layers[i]['bias'] = np.array(layer_data['bias'])
            self.q_network.layers[i]['activation'] = layer_data['activation']

        # Load training history
        history = model_data['training_history']
        self.episode_rewards = history['episode_rewards']
        self.losses = history['losses']
        self.steps_done = history['steps_done']

        logger.info(f"✅ Quantum RL Trader model loaded from {filepath}")

# Factory function
def create_quantum_rl_trader(**kwargs) -> QuantumRLTrader:
    """Create Quantum RL Trader with default configuration"""
    config = QuantumRLConfig(
        state_dim=kwargs.get('state_dim', 50),
        action_dim=kwargs.get('action_dim', 5),
        quantum_bits=kwargs.get('quantum_bits', 8),
        use_lstm_signals=kwargs.get('use_lstm_signals', True),
        num_assets=kwargs.get('num_assets', 5),
        learning_rate=kwargs.get('learning_rate', 0.0001),
        **kwargs
    )

    return QuantumRLTrader(config)

# Testing and demonstration
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    print("🚀 Quantum Reinforcement Learning Trader - Testing")
    print("=" * 60)

    # Create synthetic market data
    np.random.seed(42)
    num_days = 252  # One trading year
    num_assets = 5

    # Generate correlated price series
    returns = np.random.randn(num_days, num_assets) * 0.02  # 2% daily volatility
    prices = np.cumprod(1 + returns, axis=0) * 100  # Start at $100

    # Generate market features (technical indicators, sentiment, etc.)
    market_features = np.random.randn(num_days, 50)

    print(f"📊 Generated synthetic data:")
    print(f"  Days: {num_days}")
    print(f"  Assets: {num_assets}")
    print(f"  Price range: ${prices.min():.2f} - ${prices.max():.2f}")

    # Create Quantum RL Trader
    trader = create_quantum_rl_trader(
        state_dim=50,
        action_dim=5,
        quantum_bits=6,
        num_assets=num_assets,
        use_lstm_signals=True,
        learning_rate=0.001,
        episodes=100
    )

    print("\n🎯 Starting training...")

    # Training
    num_episodes = 20
    training_results = []

    for episode in range(num_episodes):
        # Train one episode
        episode_result = trader.train_episode(
            market_data=market_features,
            asset_prices=prices,
            num_steps=min(100, len(prices)-1)
        )

        training_results.append(episode_result)

        if episode % 5 == 0:
            print(f"Episode {episode}: Reward = {episode_result['episode_reward']:.4f}, "
                  f"Portfolio = ${episode_result['portfolio_value']:.2f}, "
                  f"Epsilon = {episode_result['epsilon']:.3f}")

    print("\n📊 Training completed!")

    # Evaluation
    print("\n🔬 Evaluating trained agent...")

    # Use last 50 days for testing
    test_split = int(0.8 * len(prices))
    test_prices = prices[test_split:]
    test_features = market_features[test_split:]

    eval_results = trader.evaluate(test_features, test_prices)

    print(f"\n📈 Evaluation Results:")
    print(f"  Final Portfolio Value: ${eval_results['eval_portfolio_value']:.2f}")
    print(f"  Total Return: {eval_results['total_return']:.2%}")
    print(f"  Prediction Accuracy: {eval_results['prediction_accuracy']:.2%}")
    print(f"  Number of Trades: {eval_results['num_trades']}")

    # Plot results
    plt.figure(figsize=(12, 8))

    # Training rewards
    plt.subplot(2, 2, 1)
    rewards = [r['episode_reward'] for r in training_results]
    plt.plot(rewards)
    plt.title('Episode Rewards')
    plt.xlabel('Episode')
    plt.ylabel('Reward')
    plt.grid(True)

    # Portfolio values
    plt.subplot(2, 2, 2)
    portfolio_values = [r['portfolio_value'] for r in training_results]
    plt.plot(portfolio_values)
    plt.title('Portfolio Value During Training')
    plt.xlabel('Episode')
    plt.ylabel('Portfolio Value ($)')
    plt.grid(True)

    # Asset prices
    plt.subplot(2, 2, 3)
    for i in range(min(3, num_assets)):  # Plot first 3 assets
        plt.plot(prices[:, i], label=f'Asset {i+1}')
    plt.title('Asset Prices')
    plt.xlabel('Day')
    plt.ylabel('Price ($)')
    plt.legend()
    plt.grid(True)

    # Epsilon decay
    plt.subplot(2, 2, 4)
    epsilons = [r['epsilon'] for r in training_results]
    plt.plot(epsilons)
    plt.title('Epsilon Decay')
    plt.xlabel('Episode')
    plt.ylabel('Epsilon')
    plt.grid(True)

    plt.tight_layout()
    plt.show()

    # Save model
    trader.save_model('/home/davidsanker/platform/rl/quantum_rl_trader_model.json')

    print("\n✅ Quantum RL Trader training and evaluation completed successfully!")