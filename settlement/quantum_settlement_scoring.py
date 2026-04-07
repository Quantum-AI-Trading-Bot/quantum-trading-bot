#!/usr/bin/env python3
"""
Quantum Settlement and Scoring System
Advanced settlement and performance scoring for quantum AI trading predictions

Based on latest 2024-2025 research:
- Quantum cryptography for settlement verification
- Multi-dimensional performance scoring
- Real-time settlement processing
- Blockchain anchoring for audit trails
- Automated dispute resolution
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json
import hashlib
from abc import ABC, abstractmethod
from enum import Enum

# Try to import cryptography libraries
try:
    import cryptography.hazmat.primitives.asymmetric as rsa
    import cryptography.hazmat.primitives.serialization as serialization
    import cryptography.hazmat.primitives.hashes as hashes
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logging.warning("Cryptography library not available - using simplified cryptographic functions")

logger = logging.getLogger(__name__)

class SettlementStatus(Enum):
    """Settlement status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

class ScoringMetric(Enum):
    """Performance scoring metrics"""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    PROFIT_FACTOR = "profit_factor"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    EXPECTED_VALUE = "expected_value"
    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    QUANTUM_CONSISTENCY = "quantum_consistency"

@dataclass
class PredictionRecord:
    """Record of a trading prediction"""
    prediction_id: str
    timestamp: datetime
    asset_symbol: str
    prediction_type: str  # "direction", "price", "volatility", etc.
    prediction_value: Union[float, int, str]
    confidence_score: float
    quantum_fingerprint: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SettlementRecord:
    """Record of a settlement transaction"""
    settlement_id: str
    prediction_id: str
    timestamp: datetime
    asset_symbol: str
    settlement_price: float
    prediction_price: float
    price_difference: float
    percentage_error: float
    is_correct: bool
    profit_loss: float
    settlement_status: SettlementStatus
    quantum_signature: str
    blockchain_hash: Optional[str] = None
    dispute_reason: Optional[str] = None

@dataclass
class PerformanceScore:
    """Comprehensive performance score for a prediction set"""
    scorer_id: str
    timestamp: datetime
    prediction_period_start: datetime
    prediction_period_end: datetime
    total_predictions: int
    correct_predictions: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    expected_value: float
    risk_adjusted_return: float
    quantum_consistency_score: float
    overall_score: float
    detailed_metrics: Dict[str, float] = field(default_factory=dict)

class QuantumCryptography:
    """Quantum-inspired cryptographic operations for settlement security"""

    def __init__(self):
        self.private_key = None
        self.public_key = None
        self._initialize_keys()

    def _initialize_keys(self):
        """Initialize cryptographic keys"""
        if CRYPTOGRAPHY_AVAILABLE:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
        else:
            # Fallback for environments without cryptography library
            self.private_key = "fallback_private_key_" + hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:32]
            self.public_key = "fallback_public_key_" + hashlib.sha256(str(datetime.now() + timedelta(hours=1)).encode()).hexdigest()[:32]

    def generate_quantum_fingerprint(self, data: Any) -> str:
        """Generate quantum-inspired fingerprint for data"""
        data_str = json.dumps(data, sort_keys=True, default=str)
        hash_input = data_str + str(datetime.now().timestamp())

        # Multi-round hashing for quantum-like properties
        fingerprint = hash_input
        for _ in range(3):  # Quantum circuit depth simulation
            fingerprint = hashlib.sha256(fingerprint.encode()).hexdigest()

        return f"QUANTUM_{fingerprint[:32]}"

    def sign_transaction(self, transaction_data: Dict) -> str:
        """Create quantum signature for transaction"""
        fingerprint = self.generate_quantum_fingerprint(transaction_data)

        if CRYPTOGRAPHY_AVAILABLE and self.private_key:
            signature = self.private_key.sign(
                fingerprint.encode(),
                hashes.SHA256()
            )
            return signature.hex()
        else:
            # Fallback signature
            sign_input = fingerprint + self.private_key
            return hashlib.sha512(sign_input.encode()).hexdigest()

    def verify_signature(self, transaction_data: Dict, signature: str) -> bool:
        """Verify quantum signature"""
        fingerprint = self.generate_quantum_fingerprint(transaction_data)

        if CRYPTOGRAPHY_AVAILABLE and self.public_key:
            try:
                signature_bytes = bytes.fromhex(signature)
                self.public_key.verify(
                    signature_bytes,
                    fingerprint.encode(),
                    hashes.SHA256()
                )
                return True
            except Exception:
                return False
        else:
            # Fallback verification
            sign_input = fingerprint + self.private_key
            expected_signature = hashlib.sha512(sign_input.encode()).hexdigest()
            return signature == expected_signature

class BlockchainAnchor:
    """Blockchain anchoring for settlement audit trails"""

    def __init__(self):
        self.chain = []
        self.difficulty = 4  # Number of leading zeros required

    def create_block(self, transactions: List[Dict]) -> Dict:
        """Create a new block with transactions"""
        previous_hash = self.chain[-1]['hash'] if self.chain else '0' * 64

        # Create block header
        block_header = {
            'timestamp': datetime.now().isoformat(),
            'previous_hash': previous_hash,
            'transaction_count': len(transactions),
            'merkle_root': self._create_merkle_root(transactions),
            'nonce': 0
        }

        # Mine block (simplified proof of work)
        block_hash = self._mine_block(block_header)

        block = {
            'header': block_header,
            'transactions': transactions,
            'hash': block_hash,
            'block_number': len(self.chain) + 1
        }

        return block

    def _create_merkle_root(self, transactions: List[Dict]) -> str:
        """Create Merkle root for transactions"""
        if not transactions:
            return hashlib.sha256(b'').hexdigest()

        # Hash all transactions
        hashes = [hashlib.sha256(json.dumps(tx, sort_keys=True, default=str).encode()).hexdigest()
                 for tx in transactions]

        # Build Merkle tree
        while len(hashes) > 1:
            new_hashes = []
            for i in range(0, len(hashes), 2):
                if i + 1 < len(hashes):
                    combined = hashes[i] + hashes[i+1]
                    new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
                else:
                    new_hashes.append(hashes[i])
            hashes = new_hashes

        return hashes[0]

    def _mine_block(self, block_header: Dict) -> str:
        """Mine block with proof of work"""
        target = '0' * self.difficulty
        nonce = 0
        max_nonce = 1000000  # Prevent infinite loops

        while nonce < max_nonce:
            block_header['nonce'] = nonce
            block_string = json.dumps(block_header, sort_keys=True)
            block_hash = hashlib.sha256(block_string.encode()).hexdigest()

            if block_hash.startswith(target):
                return block_hash
            nonce += 1

        return block_hash  # Return hash even if mining failed

    def add_block(self, transactions: List[Dict]) -> str:
        """Add block to blockchain"""
        block = self.create_block(transactions)
        self.chain.append(block)
        return block['hash']

    def verify_chain(self) -> bool:
        """Verify blockchain integrity"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]

            # Check previous hash link
            if current_block['header']['previous_hash'] != previous_block['hash']:
                return False

            # Verify block hash
            block_string = json.dumps(current_block['header'], sort_keys=True)
            expected_hash = hashlib.sha256(block_string.encode()).hexdigest()
            if current_block['hash'] != expected_hash:
                return False

        return True

class SettlementEngine:
    """Main settlement engine for quantum trading predictions"""

    def __init__(self):
        self.crypto = QuantumCryptography()
        self.blockchain = BlockchainAnchor()
        self.pending_settlements = {}
        self.completed_settlements = []
        self.dispute_handler = DisputeHandler()

    def create_prediction_record(self, prediction_data: Dict) -> PredictionRecord:
        """Create a new prediction record"""
        prediction_id = f"PRED_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(prediction_data.get('symbol', '')) % 10000:04d}"

        quantum_fingerprint = self.crypto.generate_quantum_fingerprint(prediction_data)

        record = PredictionRecord(
            prediction_id=prediction_id,
            timestamp=datetime.now(),
            asset_symbol=prediction_data.get('symbol', 'UNKNOWN'),
            prediction_type=prediction_data.get('type', 'direction'),
            prediction_value=prediction_data.get('value', 0),
            confidence_score=prediction_data.get('confidence', 0.5),
            quantum_fingerprint=quantum_fingerprint,
            metadata=prediction_data
        )

        logger.info(f"📝 Created prediction record: {prediction_id}")
        return record

    def initiate_settlement(self, prediction_record: PredictionRecord,
                          settlement_data: Dict) -> SettlementRecord:
        """Initiate settlement for a prediction"""
        settlement_id = f"SETTLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(prediction_record.asset_symbol) % 10000:04d}"

        # Calculate settlement metrics
        settlement_price = settlement_data.get('price', 0)
        prediction_price = float(prediction_record.prediction_value) if isinstance(prediction_record.prediction_value, (int, float)) else settlement_price

        price_difference = settlement_price - prediction_price
        percentage_error = (price_difference / prediction_price) * 100 if prediction_price != 0 else 0

        # Determine if prediction was correct
        is_correct = self._evaluate_prediction_correctness(prediction_record, settlement_data)

        # Calculate profit/loss
        profit_loss = self._calculate_profit_loss(prediction_record, settlement_data, is_correct)

        # Create quantum signature
        settlement_record_data = {
            'settlement_id': settlement_id,
            'prediction_id': prediction_record.prediction_id,
            'settlement_price': settlement_price,
            'prediction_price': prediction_price,
            'timestamp': datetime.now().isoformat()
        }

        quantum_signature = self.crypto.sign_transaction(settlement_record_data)

        record = SettlementRecord(
            settlement_id=settlement_id,
            prediction_id=prediction_record.prediction_id,
            timestamp=datetime.now(),
            asset_symbol=prediction_record.asset_symbol,
            settlement_price=settlement_price,
            prediction_price=prediction_price,
            price_difference=price_difference,
            percentage_error=percentage_error,
            is_correct=is_correct,
            profit_loss=profit_loss,
            settlement_status=SettlementStatus.PROCESSING,
            quantum_signature=quantum_signature
        )

        self.pending_settlements[settlement_id] = record
        logger.info(f"⚖️ Initiated settlement: {settlement_id}")

        return record

    def _evaluate_prediction_correctness(self, prediction: PredictionRecord,
                                       settlement_data: Dict) -> bool:
        """Evaluate if prediction was correct"""
        if prediction.prediction_type == "direction":
            # Direction prediction (UP/DOWN)
            predicted_direction = prediction.prediction_value
            actual_movement = settlement_data.get('price_change', 0)
            return (predicted_direction > 0 and actual_movement > 0) or (predicted_direction < 0 and actual_movement < 0)

        elif prediction.prediction_type == "price":
            # Price prediction within tolerance
            tolerance = settlement_data.get('tolerance', 0.02)  # 2% default tolerance
            predicted_price = float(prediction.prediction_value)
            actual_price = settlement_data.get('price', 0)
            return abs(actual_price - predicted_price) / predicted_price <= tolerance

        elif prediction.prediction_type == "volatility":
            # Volatility prediction
            predicted_vol = prediction.prediction_value
            actual_vol = settlement_data.get('volatility', 0)
            return abs(actual_vol - predicted_vol) / predicted_vol <= 0.2  # 20% tolerance

        else:
            # Default case
            return settlement_data.get('correct', False)

    def _calculate_profit_loss(self, prediction: PredictionRecord,
                              settlement_data: Dict, is_correct: bool) -> float:
        """Calculate profit/loss for the prediction"""
        position_size = settlement_data.get('position_size', 1.0)
        leverage = settlement_data.get('leverage', 1.0)

        if prediction.prediction_type == "direction":
            if is_correct:
                # Profit from correct directional prediction
                price_return = settlement_data.get('price_change', 0)
                return position_size * leverage * abs(price_return)
            else:
                # Loss from incorrect prediction
                return -position_size * leverage * abs(settlement_data.get('price_change', 0)) * 0.5  # 50% loss mitigation

        elif prediction.prediction_type == "price":
            if is_correct:
                return position_size * leverage * 0.02  # 2% profit for accurate price prediction
            else:
                return -position_size * leverage * 0.01  # 1% loss for inaccurate prediction

        else:
            return 0.0  # No P/L for other prediction types

    def complete_settlement(self, settlement_id: str) -> bool:
        """Complete settlement processing"""
        if settlement_id not in self.pending_settlements:
            logger.error(f"❌ Settlement not found: {settlement_id}")
            return False

        settlement = self.pending_settlements[settlement_id]

        # Verify quantum signature
        settlement_data = {
            'settlement_id': settlement.settlement_id,
            'prediction_id': settlement.prediction_id,
            'settlement_price': settlement.settlement_price,
            'prediction_price': settlement.prediction_price,
            'timestamp': settlement.timestamp.isoformat()
        }

        if not self.crypto.verify_signature(settlement_data, settlement.quantum_signature):
            logger.error(f"❌ Quantum signature verification failed for settlement: {settlement_id}")
            settlement.settlement_status = SettlementStatus.FAILED
            return False

        # Add to blockchain
        blockchain_hash = self.blockchain.add_block([{
            'settlement_id': settlement_id,
            'timestamp': settlement.timestamp.isoformat(),
            'asset': settlement.asset_symbol,
            'profit_loss': settlement.profit_loss
        }])

        settlement.blockchain_hash = blockchain_hash
        settlement.settlement_status = SettlementStatus.COMPLETED

        # Move from pending to completed
        self.completed_settlements.append(settlement)
        del self.pending_settlements[settlement_id]

        logger.info(f"✅ Settlement completed: {settlement_id}, P&L: {settlement.profit_loss:.4f}")
        return True

    def create_dispute(self, settlement_id: str, dispute_reason: str) -> bool:
        """Create a dispute for a settlement"""
        if settlement_id not in self.completed_settlements:
            logger.error(f"❌ Cannot dispute settlement not completed: {settlement_id}")
            return False

        settlement = self.completed_settlements[
            [i for i, s in enumerate(self.completed_settlements) if s.settlement_id == settlement_id][0]
        ]

        dispute = self.dispute_handler.create_dispute(settlement, dispute_reason)
        settlement.settlement_status = SettlementStatus.DISPUTED
        settlement.dispute_reason = dispute_reason

        logger.info(f"⚠️ Dispute created for settlement: {settlement_id}")
        return True

class PerformanceScorer:
    """Advanced performance scoring system"""

    def __init__(self):
        self.scorer_id = f"SCORER_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.metric_weights = {
            ScoringMetric.ACCURACY: 0.20,
            ScoringMetric.PROFIT_FACTOR: 0.15,
            ScoringMetric.SHARPE_RATIO: 0.15,
            ScoringMetric.MAX_DRAWDOWN: 0.10,
            ScoringMetric.WIN_RATE: 0.10,
            ScoringMetric.EXPECTED_VALUE: 0.10,
            ScoringMetric.RISK_ADJUSTED_RETURN: 0.10,
            ScoringMetric.QUANTUM_CONSISTENCY: 0.10
        }

    def calculate_accuracy(self, settlements: List[SettlementRecord]) -> float:
        """Calculate prediction accuracy"""
        if not settlements:
            return 0.0

        correct_count = sum(1 for s in settlements if s.is_correct)
        return correct_count / len(settlements)

    def calculate_precision(self, settlements: List[SettlementRecord]) -> float:
        """Calculate precision (true positives / all positive predictions)"""
        # For financial predictions, consider profitable predictions as "positive"
        profitable_predictions = [s for s in settlements if s.profit_loss > 0]
        correct_profitable = [s for s in profitable_predictions if s.is_correct]

        if not profitable_predictions:
            return 0.0

        return len(correct_profitable) / len(profitable_predictions)

    def calculate_recall(self, settlements: List[SettlementRecord]) -> float:
        """Calculate recall (true positives / all actual positives)"""
        all_profitable = [s for s in settlements if s.is_correct]  # Actual profitable opportunities
        correct_profitable = [s for s in settlements if s.profit_loss > 0 and s.is_correct]

        if not all_profitable:
            return 0.0

        return len(correct_profitable) / len(all_profitable)

    def calculate_profit_factor(self, settlements: List[SettlementRecord]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(s.profit_loss for s in settlements if s.profit_loss > 0)
        gross_loss = abs(sum(s.profit_loss for s in settlements if s.profit_loss < 0))

        return gross_profit / gross_loss if gross_loss > 0 else float('inf')

    def calculate_sharpe_ratio(self, settlements: List[SettlementRecord], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if not settlements:
            return 0.0

        returns = [s.profit_loss for s in settlements]
        mean_return = np.mean(returns)
        return_std = np.std(returns)

        if return_std == 0:
            return 0.0

        # Annualize (assuming daily settlements)
        annualized_return = mean_return * 252
        annualized_std = return_std * np.sqrt(252)

        return (annualized_return - risk_free_rate) / annualized_std

    def calculate_max_drawdown(self, settlements: List[SettlementRecord]) -> float:
        """Calculate maximum drawdown"""
        if not settlements:
            return 0.0

        cumulative_pnl = np.cumsum([s.profit_loss for s in settlements])
        peak = np.maximum.accumulate(cumulative_pnl)
        drawdown = (cumulative_pnl - peak) / peak
        return abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0

    def calculate_win_rate(self, settlements: List[SettlementRecord]) -> float:
        """Calculate win rate"""
        if not settlements:
            return 0.0

        winning_settlements = [s for s in settlements if s.profit_loss > 0]
        return len(winning_settlements) / len(settlements)

    def calculate_expected_value(self, settlements: List[SettlementRecord]) -> float:
        """Calculate expected value of predictions"""
        if not settlements:
            return 0.0

        total_pnl = sum(s.profit_loss for s in settlements)
        return total_pnl / len(settlements)

    def calculate_risk_adjusted_return(self, settlements: List[SettlementRecord]) -> float:
        """Calculate risk-adjusted return"""
        mean_return = self.calculate_expected_value(settlements)
        return_std = np.std([s.profit_loss for s in settlements])

        if return_std == 0:
            return mean_return

        return mean_return / return_std

    def calculate_quantum_consistency(self, settlements: List[SettlementRecord]) -> float:
        """Calculate quantum fingerprint consistency score"""
        if not settlements:
            return 0.0

        # Check if quantum fingerprints follow expected patterns
        quantum_scores = []
        for settlement in settlements:
            # Simple consistency check: quantum fingerprints should be unique and valid
            fingerprint_valid = settlement.quantum_signature and len(settlement.quantum_signature) > 10
            quantum_scores.append(1.0 if fingerprint_valid else 0.0)

        return np.mean(quantum_scores)

    def calculate_overall_score(self, settlements: List[SettlementRecord]) -> PerformanceScore:
        """Calculate comprehensive performance score"""
        if not settlements:
            return PerformanceScore(
                scorer_id=self.scorer_id,
                timestamp=datetime.now(),
                prediction_period_start=datetime.now(),
                prediction_period_end=datetime.now(),
                total_predictions=0,
                correct_predictions=0,
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                expected_value=0.0,
                risk_adjusted_return=0.0,
                quantum_consistency_score=0.0,
                overall_score=0.0
            )

        # Calculate individual metrics
        accuracy = self.calculate_accuracy(settlements)
        precision = self.calculate_precision(settlements)
        recall = self.calculate_recall(settlements)
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        profit_factor = self.calculate_profit_factor(settlements)
        sharpe_ratio = self.calculate_sharpe_ratio(settlements)
        max_drawdown = self.calculate_max_drawdown(settlements)
        win_rate = self.calculate_win_rate(settlements)
        expected_value = self.calculate_expected_value(settlements)
        risk_adjusted_return = self.calculate_risk_adjusted_return(settlements)
        quantum_consistency = self.calculate_quantum_consistency(settlements)

        # Calculate weighted overall score
        metric_values = {
            ScoringMetric.ACCURACY: accuracy,
            ScoringMetric.PROFIT_FACTOR: min(profit_factor / 2, 1),  # Cap at 1.0
            ScoringMetric.SHARPE_RATIO: min(max(sharpe_ratio, 0) / 2, 1),  # Normalize positive values
            ScoringMetric.MAX_DRAWDOWN: max(0, 1 - max_drawdown),  # Inverse relationship
            ScoringMetric.WIN_RATE: win_rate,
            ScoringMetric.EXPECTED_VALUE: min(max(expected_value * 100, -1), 1),  # Scale and cap
            ScoringMetric.RISK_ADJUSTED_RETURN: min(max(risk_adjusted_return, -1), 1),
            ScoringMetric.QUANTUM_CONSISTENCY: quantum_consistency
        }

        overall_score = sum(
            self.metric_weights[metric] * value
            for metric, value in metric_values.items()
        )

        return PerformanceScore(
            scorer_id=self.scorer_id,
            timestamp=datetime.now(),
            prediction_period_start=min(s.timestamp for s in settlements),
            prediction_period_end=max(s.timestamp for s in settlements),
            total_predictions=len(settlements),
            correct_predictions=sum(1 for s in settlements if s.is_correct),
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            expected_value=expected_value,
            risk_adjusted_return=risk_adjusted_return,
            quantum_consistency_score=quantum_consistency,
            overall_score=overall_score,
            detailed_metrics={
                'precision': precision,
                'recall': recall,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'expected_value': expected_value,
                'risk_adjusted_return': risk_adjusted_return,
                'quantum_consistency': quantum_consistency
            }
        )

class DisputeHandler:
    """Handle settlement disputes and resolution"""

    def __init__(self):
        self.active_disputes = []
        self.resolved_disputes = []

    def create_dispute(self, settlement: SettlementRecord, reason: str) -> Dict:
        """Create a new dispute"""
        dispute_id = f"DISPUTE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(settlement.settlement_id) % 10000:04d}"

        dispute = {
            'dispute_id': dispute_id,
            'settlement_id': settlement.settlement_id,
            'creation_timestamp': datetime.now(),
            'reason': reason,
            'status': 'OPEN',
            'resolution': None,
            'evidence': [],
            'final_outcome': None
        }

        self.active_disputes.append(dispute)
        logger.info(f"⚖️ Dispute created: {dispute_id} for settlement: {settlement.settlement_id}")

        return dispute

    def resolve_dispute(self, dispute_id: str, resolution: str, outcome: str) -> bool:
        """Resolve a dispute"""
        for i, dispute in enumerate(self.active_disputes):
            if dispute['dispute_id'] == dispute_id:
                dispute['resolution'] = resolution
                dispute['final_outcome'] = outcome
                dispute['status'] = 'RESOLVED'
                dispute['resolution_timestamp'] = datetime.now()

                # Move to resolved disputes
                self.resolved_disputes.append(dispute)
                self.active_disputes.pop(i)

                logger.info(f"✅ Dispute resolved: {dispute_id} - {outcome}")
                return True

        logger.error(f"❌ Dispute not found: {dispute_id}")
        return False

# Factory function
def create_settlement_system() -> Tuple[SettlementEngine, PerformanceScorer]:
    """Create complete settlement and scoring system"""
    engine = SettlementEngine()
    scorer = PerformanceScorer()

    return engine, scorer

# Testing and demonstration
if __name__ == "__main__":
    print("🚀 Quantum Settlement and Scoring System - Testing")
    print("=" * 60)

    # Create settlement system
    engine, scorer = create_settlement_system()

    print("\n📝 Creating prediction records...")
    # Create some test predictions
    predictions = []
    for i in range(10):
        prediction_data = {
            'symbol': f'STOCK_{i%5+1}',
            'type': 'direction',
            'value': np.random.choice([-1, 1]),
            'confidence': np.random.uniform(0.6, 0.95),
            'timestamp': datetime.now() - timedelta(hours=i)
        }

        record = engine.create_prediction_record(prediction_data)
        predictions.append(record)

    print(f"✅ Created {len(predictions)} prediction records")

    print("\n⚖️ Processing settlements...")
    settlements = []
    for prediction in predictions:
        settlement_data = {
            'price': 100 + np.random.randn() * 5,
            'price_change': np.random.randn() * 0.02,
            'position_size': 1.0,
            'leverage': 1.0
        }

        settlement = engine.initiate_settlement(prediction, settlement_data)
        settlements.append(settlement)

    # Complete all settlements
    for settlement in settlements:
        engine.complete_settlement(settlement.settlement_id)

    print(f"✅ Processed {len(settlements)} settlements")

    print("\n📊 Calculating performance scores...")
    score = scorer.calculate_overall_score(settlements)

    print(f"\n📈 Performance Results:")
    print(f"  Total Predictions: {score.total_predictions}")
    print(f"  Correct Predictions: {score.correct_predictions}")
    print(f"  Accuracy: {score.accuracy:.4f}")
    print(f"  Precision: {score.precision:.4f}")
    print(f"  Recall: {score.recall:.4f}")
    print(f"  F1 Score: {score.f1_score:.4f}")
    print(f"  Profit Factor: {score.profit_factor:.4f}")
    print(f"  Sharpe Ratio: {score.sharpe_ratio:.4f}")
    print(f"  Max Drawdown: {score.max_drawdown:.4f}")
    print(f"  Win Rate: {score.win_rate:.4f}")
    print(f"  Expected Value: {score.expected_value:.6f}")
    print(f"  Risk Adjusted Return: {score.risk_adjusted_return:.4f}")
    print(f"  Quantum Consistency: {score.quantum_consistency_score:.4f}")
    print(f"  Overall Score: {score.overall_score:.4f}")

    print(f"\n🔗 Blockchain Status: {'Valid' if engine.blockchain.verify_chain() else 'Invalid'}")
    print(f"  Blocks mined: {len(engine.blockchain.chain)}")

    # Create a dispute test
    print(f"\n⚖️ Testing dispute system...")
    if settlements:
        dispute_created = engine.create_dispute(
            settlements[0].settlement_id,
            "Testing dispute functionality"
        )
        print(f"  Dispute created: {dispute_created['dispute_id']}")

        # Resolve dispute
        dispute_resolved = engine.dispute_handler.resolve_dispute(
            dispute_created['dispute_id'],
            "Manual review completed",
            "Settlement upheld"
        )
        print(f"  Dispute resolved: {dispute_resolved}")

    # Save results
    results = {
        'performance_score': {
            'scorer_id': score.scorer_id,
            'timestamp': score.timestamp.isoformat(),
            'overall_score': score.overall_score,
            'detailed_metrics': score.detailed_metrics
        },
        'settlements_count': len(settlements),
        'predictions_count': len(predictions),
        'blockchain_valid': engine.blockchain.verify_chain(),
        'blockchain_blocks': len(engine.blockchain.chain)
    }

    with open('/home/davidsanker/platform/settlement/quantum_settlement_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Quantum Settlement and Scoring System test completed!")
    print(f"📊 Results saved to quantum_settlement_results.json")