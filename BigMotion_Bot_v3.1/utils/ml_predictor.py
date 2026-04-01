"""ML Predictor with Fallback - Fixed Version"""
import numpy as np
import pandas as pd
import pickle
import logging
from pathlib import Path
from typing import Tuple
import warnings

# Suppress sklearn warnings
warnings.filterwarnings('ignore', category=UserWarning)

logger = logging.getLogger(__name__)


class MLPredictor:
    def __init__(self, model_path: str = None):
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.model_loaded = False
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            logger.warning("ML model not found. Using fallback logic.")
    
    def load_model(self, model_path: str) -> bool:
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data.get('model')
            self.scaler = model_data.get('scaler')
            self.feature_columns = model_data.get('feature_columns', [])
            
            if self.model:
                self.model_loaded = True
                logger.info("ML model loaded")
                return True
            return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def predict(self, features: np.ndarray) -> Tuple[float, str]:
        if not self.model_loaded:
            return self._fallback_prediction(features)
        
        try:
            # Convert to DataFrame with proper column names
            if self.feature_columns:
                features_df = pd.DataFrame([features], columns=self.feature_columns)
            else:
                features_df = pd.DataFrame([features])
            
            # Scale features
            if self.scaler:
                features_scaled = self.scaler.transform(features_df)
            else:
                features_scaled = features_df.values
            
            # Make prediction
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(features_scaled)[0]
                pred = self.model.predict(features_scaled)[0]
                confidence = np.max(proba)
                signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
                signal = signal_map.get(pred, 'HOLD')
            else:
                pred = self.model.predict(features_scaled)[0]
                if pred > 0.5:
                    signal, confidence = 'BUY', min(pred, 1.0)
                elif pred < -0.5:
                    signal, confidence = 'SELL', min(abs(pred), 1.0)
                else:
                    signal, confidence = 'HOLD', 0.5
            
            return confidence, signal
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return self._fallback_prediction(features)
    
    def _fallback_prediction(self, features: np.ndarray) -> Tuple[float, str]:
        try:
            if len(features) < 7:
                return 0.5, 'HOLD'
            
            rsi, adx = features[0], features[1]
            ema_20, ema_50, ema_200 = features[3], features[4], features[5]
            
            uptrend = ema_20 > ema_50 > ema_200
            downtrend = ema_20 < ema_50 < ema_200
            
            if uptrend and 40 < rsi < 70 and adx > 20:
                return min(0.65 + (adx - 20) / 100, 0.85), 'BUY'
            elif downtrend and 30 < rsi < 60 and adx > 20:
                return min(0.65 + (adx - 20) / 100, 0.85), 'SELL'
            
            return 0.5, 'HOLD'
        except:
            return 0.5, 'HOLD'
