"""
ML Model Trainer for Deep Financial Analysis
Uses collected training data to improve analysis predictions:
- Overall rating accuracy
- Valuation predictions  
- Risk assessments
- Growth estimates
- Bull/Bear debate outcomes
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, mean_squared_error, r2_score
import pickle
from concurrent.futures import ThreadPoolExecutor


class AnalysisModelTrainer:
    """
    Trains ML models on collected deep analysis data to improve:
    1. Rating classification (Buy/Hold/Sell)
    2. Score regression (0-100 overall score)
    3. Direction prediction (UP/DOWN stock movement)
    4. Risk assessment accuracy
    5. Growth estimate accuracy
    """

    def __init__(self, model_dir: Optional[str] = None):
        if model_dir:
            self.model_dir = Path(model_dir)
        else:
            self.model_dir = Path(__file__).parent.parent / "models" / "analysis_models"

        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Model paths
        self.rating_classifier_path = self.model_dir / "rating_classifier.pkl"
        self.score_regressor_path = self.model_dir / "score_regressor.pkl"
        self.direction_classifier_path = self.model_dir / "direction_classifier.pkl"
        self.risk_model_path = self.model_dir / "risk_model.pkl"
        self.growth_model_path = self.model_dir / "growth_model.pkl"

        # Initialize models
        self.rating_classifier = None
        self.score_regressor = None
        self.direction_classifier = None
        self.risk_model = None
        self.growth_model = None

        # Scalers
        self.scaler_rating = None
        self.scaler_score = None
        self.scaler_direction = None

        # Load existing models if available
        self._load_models()

    def _load_models(self):
        """Load pre-trained models if available"""
        try:
            if self.rating_classifier_path.exists():
                with open(self.rating_classifier_path, 'rb') as f:
                    self.rating_classifier = pickle.load(f)
                print(f"✓ Loaded rating classifier from {self.rating_classifier_path}")

            if self.score_regressor_path.exists():
                with open(self.score_regressor_path, 'rb') as f:
                    self.score_regressor = pickle.load(f)
                print(f"✓ Loaded score regressor from {self.score_regressor_path}")

            if self.direction_classifier_path.exists():
                with open(self.direction_classifier_path, 'rb') as f:
                    self.direction_classifier = pickle.load(f)
                print(f"✓ Loaded direction classifier from {self.direction_classifier_path}")

            if self.risk_model_path.exists():
                with open(self.risk_model_path, 'rb') as f:
                    self.risk_model = pickle.load(f)
                print(f"✓ Loaded risk model from {self.risk_model_path}")

            if self.growth_model_path.exists():
                with open(self.growth_model_path, 'rb') as f:
                    self.growth_model = pickle.load(f)
                print(f"✓ Loaded growth model from {self.growth_model_path}")

        except Exception as e:
            print(f"⚠️ Could not load some models: {e}")

    def _save_models(self):
        """Save all trained models"""
        try:
            if self.rating_classifier:
                with open(self.rating_classifier_path, 'wb') as f:
                    pickle.dump(self.rating_classifier, f)

            if self.score_regressor:
                with open(self.score_regressor_path, 'wb') as f:
                    pickle.dump(self.score_regressor, f)

            if self.direction_classifier:
                with open(self.direction_classifier_path, 'wb') as f:
                    pickle.dump(self.direction_classifier, f)

            if self.risk_model:
                with open(self.risk_model_path, 'wb') as f:
                    pickle.dump(self.risk_model, f)

            if self.growth_model:
                with open(self.growth_model_path, 'wb') as f:
                    pickle.dump(self.growth_model, f)

            print("✓ All models saved successfully")
        except Exception as e:
            print(f"⚠️ Failed to save models: {e}")

    def train_all_models(self, training_data_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Train all models on collected training data

        Args:
            training_data_path: Path to training data CSV (optional)

        Returns:
            Dictionary with training metrics for all models
        """
        try:
            # Load training data
            if training_data_path and Path(training_data_path).exists():
                df = pd.read_csv(training_data_path)
            else:
                # Import here to avoid circular imports
                from services.analysis_training_collector import analysis_training_collector
                df = analysis_training_collector.get_training_dataset()

            if df is None or df.empty:
                return {
                    "status": "failed",
                    "message": "No training data available"
                }

            print(f"\n🤖 Training models on {len(df)} samples...")

            metrics = {}

            # Train rating classifier
            rating_metrics = self._train_rating_classifier(df)
            metrics['rating_classifier'] = rating_metrics

            # Train score regressor
            score_metrics = self._train_score_regressor(df)
            metrics['score_regressor'] = score_metrics

            # Train direction classifier
            direction_metrics = self._train_direction_classifier(df)
            metrics['direction_classifier'] = direction_metrics

            # Train risk model
            risk_metrics = self._train_risk_model(df)
            metrics['risk_model'] = risk_metrics

            # Train growth model
            growth_metrics = self._train_growth_model(df)
            metrics['growth_model'] = growth_metrics

            # Save all models
            self._save_models()

            return {
                "status": "success",
                "training_samples": len(df),
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"⚠️ Training failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "failed",
                "message": str(e)
            }

    def _train_rating_classifier(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train model to predict rating classification (Buy/Hold/Sell)

        Features: component scores, health score, risk score, moat, growth
        Target: rating label
        """
        try:
            # Prepare features
            feature_cols = [col for col in df.columns if col.endswith('_score') or col in [
                'health_score', 'risk_score', 'moat_rating', 'growth_potential',
                'bull_strength', 'bear_strength', 'dcf_upside'
            ]]

            # Filter to available columns
            available_features = [col for col in feature_cols if col in df.columns]

            if len(available_features) < 3:
                return {"status": "skipped", "reason": "Insufficient features"}

            X = df[available_features].fillna(0)

            # Create rating labels if not present
            if 'rating' not in df.columns:
                # Generate from overall_score
                if 'overall_score' in df.columns:
                    def score_to_rating(score):
                        if score >= 80: return 'Strong Buy'
                        if score >= 65: return 'Buy'
                        if score >= 50: return 'Hold'
                        if score >= 35: return 'Sell'
                        return 'Strong Sell'
                    df['rating'] = df['overall_score'].apply(score_to_rating)
                else:
                    return {"status": "skipped", "reason": "No rating or overall_score column"}

            y = df['rating']

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            self.scaler_rating = StandardScaler()
            X_train_scaled = self.scaler_rating.fit_transform(X_train)
            X_test_scaled = self.scaler_rating.transform(X_test)

            # Train model
            model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)

            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)

            self.rating_classifier = {
                'model': model,
                'scaler': self.scaler_rating,
                'features': available_features
            }

            return {
                "status": "trained",
                "accuracy": round(accuracy, 3),
                "cv_accuracy_mean": round(cv_scores.mean(), 3),
                "cv_accuracy_std": round(cv_scores.std(), 3),
                "features_used": available_features,
                "classes": list(y.unique())
            }

        except Exception as e:
            print(f"⚠️ Rating classifier training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _train_score_regressor(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train model to predict overall score (0-100)

        Features: component scores, health, risk, moat, growth
        Target: overall_score or price_change_pct (actual)
        """
        try:
            # Prepare features
            feature_cols = [col for col in df.columns if col.endswith('_score') or col in [
                'health_score', 'risk_score', 'moat_rating', 'growth_potential',
                'bull_strength', 'bear_strength', 'dcf_upside'
            ]]

            available_features = [col for col in feature_cols if col in df.columns]

            if len(available_features) < 3:
                return {"status": "skipped", "reason": "Insufficient features"}

            X = df[available_features].fillna(0)

            # Target: prefer actual price change, fallback to predicted score
            if 'price_change_pct' in df.columns:
                y = df['price_change_pct']
                target_col = 'price_change_pct'
            elif 'overall_score' in df.columns:
                y = df['overall_score']
                target_col = 'overall_score'
            else:
                return {"status": "skipped", "reason": "No target column available"}

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            self.scaler_score = StandardScaler()
            X_train_scaled = self.scaler_score.fit_transform(X_train)
            X_test_scaled = self.scaler_score.transform(X_test)

            # Train model
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=4,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')

            self.score_regressor = {
                'model': model,
                'scaler': self.scaler_score,
                'features': available_features
            }

            return {
                "status": "trained",
                "mse": round(mse, 3),
                "rmse": round(np.sqrt(mse), 3),
                "r2_score": round(r2, 3),
                "cv_r2_mean": round(cv_scores.mean(), 3),
                "target_column": target_col,
                "features_used": available_features
            }

        except Exception as e:
            print(f"⚠️ Score regressor training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _train_direction_classifier(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train model to predict stock direction (UP/DOWN)

        Features: analysis scores, bull/bear verdict, DCF upside
        Target: actual_direction (UP/DOWN)
        """
        try:
            # Prepare features
            feature_cols = [col for col in df.columns if col.endswith('_score') or col in [
                'health_score', 'risk_score', 'moat_rating', 'growth_potential',
                'bull_strength', 'bear_strength', 'dcf_upside', 'bull_bear_verdict'
            ]]

            available_features = [col for col in feature_cols if col in df.columns]

            if len(available_features) < 3:
                return {"status": "skipped", "reason": "Insufficient features"}

            X = df[available_features].fillna(0)

            # Target: actual direction
            if 'actual_direction' not in df.columns:
                # Generate from price change if available
                if 'price_change_pct' in df.columns:
                    df['actual_direction'] = df['price_change_pct'].apply(
                        lambda x: 'UP' if x > 0 else 'DOWN'
                    )
                else:
                    return {"status": "skipped", "reason": "No actual_direction or price_change_pct"}

            y = df['actual_direction']

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            self.scaler_direction = StandardScaler()
            X_train_scaled = self.scaler_direction.fit_transform(X_train)
            X_test_scaled = self.scaler_direction.transform(X_test)

            # Train model
            model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight='balanced'
            )
            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)

            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5)

            self.direction_classifier = {
                'model': model,
                'scaler': self.scaler_direction,
                'features': available_features
            }

            return {
                "status": "trained",
                "accuracy": round(accuracy, 3),
                "cv_accuracy_mean": round(cv_scores.mean(), 3),
                "cv_accuracy_std": round(cv_scores.std(), 3),
                "features_used": available_features
            }

        except Exception as e:
            print(f"⚠️ Direction classifier training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _train_risk_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train model to predict risk assessment accuracy

        Features: risk score, volatility, debt, sector indicators
        Target: actual volatility or risk-adjusted performance
        """
        try:
            # Simple risk model based on available data
            if 'risk_score' not in df.columns:
                return {"status": "skipped", "reason": "No risk_score column"}

            feature_cols = [col for col in df.columns if col in [
                'health_score', 'moat_rating', 'growth_potential',
                'bull_strength', 'bear_strength', 'dcf_upside'
            ]]

            available_features = [col for col in feature_cols if col in df.columns]

            if len(available_features) < 2:
                return {"status": "skipped", "reason": "Insufficient features"}

            X = df[available_features].fillna(0)
            y = df['risk_score']

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Train model
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            self.risk_model = {
                'model': model,
                'features': available_features
            }

            return {
                "status": "trained",
                "mse": round(mse, 3),
                "r2_score": round(r2, 3),
                "features_used": available_features
            }

        except Exception as e:
            print(f"⚠️ Risk model training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def _train_growth_model(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train model to predict growth potential accuracy

        Features: growth factors, sector, market conditions
        Target: actual price change or growth estimate
        """
        try:
            if 'growth_potential' not in df.columns:
                return {"status": "skipped", "reason": "No growth_potential column"}

            feature_cols = [col for col in df.columns if col in [
                'health_score', 'risk_score', 'moat_rating',
                'bull_strength', 'bear_strength', 'dcf_upside'
            ]]

            available_features = [col for col in feature_cols if col in df.columns]

            if len(available_features) < 2:
                return {"status": "skipped", "reason": "Insufficient features"}

            X = df[available_features].fillna(0)

            # Target: prefer actual price change
            if 'price_change_pct' in df.columns:
                y = df['price_change_pct']
                target_col = 'price_change_pct'
            else:
                y = df['growth_potential']
                target_col = 'growth_potential'

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Train model
            model = GradientBoostingRegressor(
                n_estimators=50,
                learning_rate=0.1,
                max_depth=3,
                random_state=42
            )
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            self.growth_model = {
                'model': model,
                'features': available_features
            }

            return {
                "status": "trained",
                "mse": round(mse, 3),
                "r2_score": round(r2, 3),
                "target_column": target_col,
                "features_used": available_features
            }

        except Exception as e:
            print(f"⚠️ Growth model training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def predict_rating(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Predict rating classification using trained model

        Args:
            features: Dictionary with feature values

        Returns:
            Prediction with rating and confidence
        """
        if not self.rating_classifier:
            return None

        try:
            model = self.rating_classifier['model']
            scaler = self.rating_classifier['scaler']
            feature_names = self.rating_classifier['features']

            # Prepare features
            X = pd.DataFrame([features])
            X = X.reindex(columns=feature_names, fill_value=0)
            X_scaled = scaler.transform(X)

            # Predict
            prediction = model.predict(X_scaled)
            probabilities = model.predict_proba(X_scaled)

            # Get confidence
            classes = model.classes_
            max_prob_idx = np.argmax(probabilities[0])
            confidence = probabilities[0][max_prob_idx]

            return {
                "predicted_rating": prediction[0],
                "confidence": round(float(confidence), 3),
                "probabilities": {cls: round(float(prob), 3) for cls, prob in zip(classes, probabilities[0])}
            }
        except Exception as e:
            print(f"⚠️ Rating prediction failed: {e}")
            return None

    def predict_score(self, features: Dict[str, Any]) -> Optional[float]:
        """
        Predict overall score using trained model

        Args:
            features: Dictionary with feature values

        Returns:
            Predicted score (0-100)
        """
        if not self.score_regressor:
            return None

        try:
            model = self.score_regressor['model']
            scaler = self.score_regressor['scaler']
            feature_names = self.score_regressor['features']

            # Prepare features
            X = pd.DataFrame([features])
            X = X.reindex(columns=feature_names, fill_value=0)
            X_scaled = scaler.transform(X)

            # Predict
            prediction = model.predict(X_scaled)

            return round(float(prediction[0]), 1)
        except Exception as e:
            print(f"⚠️ Score prediction failed: {e}")
            return None

    def predict_direction(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Predict stock direction using trained model

        Args:
            features: Dictionary with feature values

        Returns:
            Prediction with direction and confidence
        """
        if not self.direction_classifier:
            return None

        try:
            model = self.direction_classifier['model']
            scaler = self.direction_classifier['scaler']
            feature_names = self.direction_classifier['features']

            # Prepare features
            X = pd.DataFrame([features])
            X = X.reindex(columns=feature_names, fill_value=0)
            X_scaled = scaler.transform(X)

            # Predict
            prediction = model.predict(X_scaled)
            probabilities = model.predict_proba(X_scaled)

            # Get confidence
            classes = model.classes_
            max_prob_idx = np.argmax(probabilities[0])
            confidence = probabilities[0][max_prob_idx]

            return {
                "predicted_direction": prediction[0],
                "confidence": round(float(confidence), 3),
                "probability_up": round(float(probabilities[0][list(classes).index('UP')]) if 'UP' in classes else 0, 3),
                "probability_down": round(float(probabilities[0][list(classes).index('DOWN')]) if 'DOWN' in classes else 0, 3)
            }
        except Exception as e:
            print(f"⚠️ Direction prediction failed: {e}")
            return None

    def get_model_status(self) -> Dict[str, Any]:
        """
        Get status of all trained models

        Returns:
            Dictionary with model status information
        """
        return {
            "rating_classifier": {
                "trained": self.rating_classifier is not None,
                "path": str(self.rating_classifier_path)
            },
            "score_regressor": {
                "trained": self.score_regressor is not None,
                "path": str(self.score_regressor_path)
            },
            "direction_classifier": {
                "trained": self.direction_classifier is not None,
                "path": str(self.direction_classifier_path)
            },
            "risk_model": {
                "trained": self.risk_model is not None,
                "path": str(self.risk_model_path)
            },
            "growth_model": {
                "trained": self.growth_model is not None,
                "path": str(self.growth_model_path)
            },
            "model_directory": str(self.model_dir)
        }


# Singleton instance
analysis_model_trainer = AnalysisModelTrainer()
