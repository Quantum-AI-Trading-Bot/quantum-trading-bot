#!/usr/bin/env python3
"""
Phase 1: ML Model Training Pipeline
Trains and evaluates machine learning models for trading
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import json

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Available model types"""
    LOGISTIC_REGRESSION = "logistic_regression"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"


@dataclass
class ModelEvaluation:
    """Model evaluation metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    cv_scores: List[float]
    feature_importance: Dict[str, float]


class MLTrainer:
    """
    Machine learning model training pipeline
    """

    def __init__(
        self,
        model_type: ModelType = ModelType.RANDOM_FOREST,
        test_size: float = 0.2,
        random_state: int = 42,
        cv_folds: int = 5
    ):
        """
        Initialize ML trainer

        Args:
            model_type: Type of model to train
            test_size: Proportion of data for testing
            random_state: Random state for reproducibility
            cv_folds: Number of cross-validation folds
        """
        self.model_type = model_type
        self.test_size = test_size
        self.random_state = random_state
        self.cv_folds = cv_folds

        self.model = None
        self.feature_names = None
        self.scaler = None

        logger.info(f"MLTrainer initialized with {model_type.value}")

    def prepare_data(
        self,
        data: pd.DataFrame,
        target_col: str = 'Target',
        feature_cols: List[str] = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for training

        Args:
            data: DataFrame with features and target
            target_col: Name of target column
            feature_cols: List of feature column names

        Returns:
            Tuple of (X, y) features and target
        """
        # Select features
        if feature_cols is None:
            # Select numeric columns excluding target
            exclude_cols = [target_col, 'Symbol', 'Data_Source', 'Fetch_Date']
            feature_cols = [col for col in data.columns
                          if col not in exclude_cols
                          and data[col].dtype in ['float64', 'int64']]

        # Remove rows with missing values
        data_clean = data[feature_cols + [target_col]].dropna()

        X = data_clean[feature_cols]
        y = (data_clean[target_col] > 0).astype(int)  # Binary classification: up or down

        self.feature_names = feature_cols

        logger.info(f"Prepared {len(X)} samples with {len(feature_cols)} features")
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")

        return X, y

    def split_data(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split data into train and test sets

        Args:
            X: Features
            y: Target

        Returns:
            Tuple of (X_train, X_test, y_train, y_test)
        """
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state, stratify=y
        )

        logger.info(f"Train set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")

        return X_train, X_test, y_train, y_test

    def create_model(self):
        """Create model based on model_type"""
        if self.model_type == ModelType.LOGISTIC_REGRESSION:
            self.model = LogisticRegression(random_state=self.random_state, max_iter=1000)

        elif self.model_type == ModelType.RANDOM_FOREST:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=self.random_state
            )

        elif self.model_type == ModelType.GRADIENT_BOOSTING:
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=self.random_state
            )

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

        logger.info(f"Created model: {self.model_type.value}")

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series
    ):
        """
        Train the model

        Args:
            X_train: Training features
            y_train: Training target
        """
        if self.model is None:
            self.create_model()

        logger.info("Training model...")
        self.model.fit(X_train, y_train)
        logger.info("Model training complete")

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        X_train: pd.DataFrame = None,
        y_train: pd.Series = None
    ) -> ModelEvaluation:
        """
        Evaluate model performance

        Args:
            X_test: Test features
            y_test: Test target
            X_train: Training features (for CV)
            y_train: Training target (for CV)

        Returns:
            ModelEvaluation object with metrics
        """
        # Predictions
        y_pred = self.model.predict(X_test)

        # Metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='binary')
        recall = recall_score(y_test, y_pred, average='binary')
        f1 = f1_score(y_test, y_pred, average='binary')

        logger.info(f"Accuracy: {accuracy:.4f}")
        logger.info(f"Precision: {precision:.4f}")
        logger.info(f"Recall: {recall:.4f}")
        logger.info(f"F1 Score: {f1:.4f}")

        # Cross-validation
        cv_scores = []
        if X_train is not None and y_train is not None:
            cv_scores = cross_val_score(self.model, X_train, y_train, cv=self.cv_folds, scoring='accuracy')
            logger.info(f"CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

        # Feature importance
        feature_importance = {}
        if hasattr(self.model, 'feature_importances_'):
            for feature, importance in zip(self.feature_names, self.model.feature_importances_):
                feature_importance[feature] = float(importance)

            # Sort by importance
            feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

            logger.info("Top 10 Features:")
            for i, (feature, importance) in enumerate(list(feature_importance.items())[:10]):
                logger.info(f"  {i+1}. {feature}: {importance:.4f}")

        return ModelEvaluation(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            cv_scores=cv_scores.tolist() if len(cv_scores) > 0 else [],
            feature_importance=feature_importance
        )

    def save_model(self, filepath: str):
        """Save trained model to file"""
        if self.model is None:
            raise ValueError("No model to save")

        model_data = {
            'model': self.model,
            'model_type': self.model_type.value,
            'feature_names': self.feature_names,
            'metadata': {
                'test_size': self.test_size,
                'random_state': self.random_state,
                'cv_folds': self.cv_folds
            }
        }

        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str):
        """Load trained model from file"""
        model_data = joblib.load(filepath)

        self.model = model_data['model']
        self.model_type = ModelType(model_data['model_type'])
        self.feature_names = model_data['feature_names']

        logger.info(f"Model loaded from {filepath}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if self.model is None:
            raise ValueError("No model available for prediction")

        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict class probabilities"""
        if self.model is None:
            raise ValueError("No model available for prediction")

        return self.model.predict_proba(X)


def train_and_evaluate(
    data: pd.DataFrame,
    model_type: ModelType = ModelType.RANDOM_FOREST,
    target_col: str = 'Target'
) -> Tuple[MLTrainer, ModelEvaluation]:
    """
    Convenience function to train and evaluate a model

    Args:
        data: DataFrame with features and target
        model_type: Type of model to train
        target_col: Name of target column

    Returns:
        Tuple of (trainer, evaluation)
    """
    # Initialize trainer
    trainer = MLTrainer(model_type=model_type)

    # Prepare data
    X, y = trainer.prepare_data(data, target_col=target_col)
    X_train, X_test, y_train, y_test = trainer.split_data(X, y)

    # Train model
    trainer.train(X_train, y_train)

    # Evaluate
    evaluation = trainer.evaluate(X_test, y_test, X_train, y_train)

    return trainer, evaluation


if __name__ == "__main__":
    # Test the ML trainer
    from data.fetch_price_data import fetch_price_data
    from data.feature_engineering import add_technical_indicators, prepare_features

    logger.info("Testing ML Trainer...")

    # Fetch and prepare data
    symbol = "AAPL"
    start_date = "2023-01-01"
    end_date = "2025-01-01"

    logger.info(f"\nFetching {symbol} data...")
    data = fetch_price_data(symbol, start_date, end_date)

    if data is not None:
        logger.info(f"\nAdding technical indicators...")
        data_with_indicators = add_technical_indicators(data)

        logger.info(f"\nPreparing features...")
        X, y, feature_cols = prepare_features(data_with_indicators)

        # Combine for training
        train_data = data_with_indicators.copy()
        train_data['Target'] = y

        logger.info(f"\n{'='*60}")
        logger.info("Training Random Forest Model")
        logger.info(f"{'='*60}\n")

        trainer, evaluation = train_and_evaluate(
            train_data,
            model_type=ModelType.RANDOM_FOREST
        )

        logger.info(f"\n{'='*60}")
        logger.info("Training Complete!")
        logger.info(f"{'='*60}\n")

        logger.info(f"Final Metrics:")
        logger.info(f"  Accuracy: {evaluation.accuracy:.4f}")
        logger.info(f"  Precision: {evaluation.precision:.4f}")
        logger.info(f"  Recall: {evaluation.recall:.4f}")
        logger.info(f"  F1 Score: {evaluation.f1_score:.4f}")

        # Save model
        model_path = f"models/{symbol}_rf_model.joblib"
        trainer.save_model(model_path)
