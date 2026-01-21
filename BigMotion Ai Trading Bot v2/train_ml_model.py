"""
ML Model Trainer for Forex Trading Bot
Trains models on historical data to predict winning trades
"""
import os
import sys
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pickle
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

print("=" * 70)
print("🤖 ML MODEL TRAINER FOR FOREX TRADING BOT")
print("=" * 70)
print()

# Configuration
SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
TIMEFRAME = mt5.TIMEFRAME_H1
BARS_TO_FETCH = 5000  # Historical bars per symbol
MODEL_SAVE_PATH = 'models/trading_model.pkl'


def initialize_mt5():
    """Initialize MT5 connection"""
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        sys.exit(1)
    print("✅ Connected to MT5")


def fetch_historical_data(symbol: str, bars: int = BARS_TO_FETCH) -> pd.DataFrame:
    """Fetch historical price data from MT5"""
    print(f"📊 Fetching {bars} bars for {symbol}...")
    
    rates = mt5.copy_rates_from_pos(symbol, TIMEFRAME, 0, bars)
    
    if rates is None or len(rates) == 0:
        print(f"⚠️  No data for {symbol}")
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['symbol'] = symbol
    
    print(f"✅ Fetched {len(df)} bars for {symbol}")
    return df


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators"""
    
    # EMA
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # ATR
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    
    # ADX
    plus_dm = df['high'].diff()
    minus_dm = -df['low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    atr_adx = tr.rolling(window=14).mean()
    plus_di = 100 * (plus_dm.rolling(window=14).mean() / atr_adx)
    minus_di = 100 * (minus_dm.rolling(window=14).mean() / atr_adx)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.rolling(window=14).mean()
    
    # MACD
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    df['bb_std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # Trend indicators
    df['trend_bull'] = (df['ema_20'] > df['ema_50']) & (df['ema_50'] > df['ema_200'])
    df['trend_bear'] = (df['ema_20'] < df['ema_50']) & (df['ema_50'] < df['ema_200'])
    
    # Price action
    df['price_change'] = df['close'].pct_change()
    df['volatility'] = df['price_change'].rolling(window=20).std()
    
    # Time features
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
    
    return df


def create_labels(df: pd.DataFrame, forward_bars: int = 10) -> pd.DataFrame:
    """
    Create labels for ML training
    Label = 1 if price moves favorably in next N bars, else 0
    """
    # For trend following: predict if trend continues
    df['future_high'] = df['high'].shift(-forward_bars)
    df['future_low'] = df['low'].shift(-forward_bars)
    
    # For BULL trend: label=1 if price goes up
    df['label_bull'] = (df['future_high'] > df['close'] * 1.001).astype(int)
    
    # For BEAR trend: label=1 if price goes down
    df['label_bear'] = (df['future_low'] < df['close'] * 0.999).astype(int)
    
    # Combined label: 1=profitable trade opportunity, 0=no trade
    df['label'] = 0
    df.loc[df['trend_bull'] & df['label_bull'], 'label'] = 1
    df.loc[df['trend_bear'] & df['label_bear'], 'label'] = 1
    
    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare feature set for ML"""
    
    feature_columns = [
        'rsi', 'adx', 'atr',
        'ema_20', 'ema_50', 'ema_200',
        'macd', 'macd_signal', 'macd_hist',
        'bb_position',
        'trend_bull', 'trend_bear',
        'price_change', 'volatility',
        'hour', 'day_of_week',
        'close', 'tick_volume'
    ]
    
    # Remove rows with NaN
    df = df.dropna(subset=feature_columns + ['label'])
    
    return df, feature_columns


def train_random_forest(X_train, X_test, y_train, y_test, scaler):
    """Train Random Forest Classifier"""
    print("\n🌲 Training Random Forest...")
    
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    
    rf.fit(X_train, y_train)
    
    # Predictions
    y_pred = rf.predict(X_test)
    y_pred_proba = rf.predict_proba(X_test)
    
    # Metrics
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"✅ Random Forest Accuracy: {accuracy:.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['No Trade', 'Trade']))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n📊 Top 10 Important Features:")
    print(feature_importance.head(10))
    
    return rf, accuracy, feature_importance


def train_gradient_boosting(X_train, X_test, y_train, y_test, scaler):
    """Train Gradient Boosting Classifier"""
    print("\n🚀 Training Gradient Boosting...")
    
    gb = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=10,
        random_state=42
    )
    
    gb.fit(X_train, y_train)
    
    # Predictions
    y_pred = gb.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"✅ Gradient Boosting Accuracy: {accuracy:.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['No Trade', 'Trade']))
    
    return gb, accuracy


def plot_confusion_matrix(y_test, y_pred, model_name):
    """Plot confusion matrix"""
    cm = confusion_matrix(y_test, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f'Confusion Matrix - {model_name}')
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.savefig(f'models/{model_name}_confusion_matrix.png')
    plt.close()
    
    print(f"✅ Saved confusion matrix: models/{model_name}_confusion_matrix.png")


def save_model(model, scaler, feature_columns, accuracy, model_name):
    """Save trained model"""
    os.makedirs('models', exist_ok=True)
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_columns,
        'accuracy': accuracy,
        'model_name': model_name,
        'trained_date': datetime.now().isoformat(),
        'symbols': SYMBOLS
    }
    
    with open(MODEL_SAVE_PATH, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n✅ Model saved to: {MODEL_SAVE_PATH}")
    print(f"📊 Model Accuracy: {accuracy:.2%}")
    print(f"🎯 Model Type: {model_name}")


def main():
    """Main training pipeline"""
    
    print("Step 1: Initialize MT5")
    initialize_mt5()
    
    print("\nStep 2: Fetch Historical Data")
    all_data = []
    
    for symbol in SYMBOLS:
        df = fetch_historical_data(symbol, BARS_TO_FETCH)
        if df is not None:
            all_data.append(df)
    
    if not all_data:
        print("❌ No data fetched. Exiting.")
        mt5.shutdown()
        sys.exit(1)
    
    # Combine all symbols
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\n✅ Total bars collected: {len(combined_df)}")
    
    print("\nStep 3: Calculate Indicators")
    combined_df = calculate_all_indicators(combined_df)
    
    print("\nStep 4: Create Labels")
    combined_df = create_labels(combined_df, forward_bars=10)
    
    print("\nStep 5: Prepare Features")
    combined_df, feature_columns = prepare_features(combined_df)
    
    print(f"\n✅ Dataset ready: {len(combined_df)} samples")
    print(f"   - Trade opportunities (label=1): {combined_df['label'].sum()}")
    print(f"   - No trade (label=0): {(combined_df['label']==0).sum()}")
    
    # Prepare X and y
    X = combined_df[feature_columns]
    y = combined_df['label']
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\n📊 Train set: {len(X_train)} samples")
    print(f"📊 Test set: {len(X_test)} samples")
    
    # Scale features
    print("\nStep 6: Scale Features")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Convert back to DataFrame for feature names
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=feature_columns)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=feature_columns)
    
    # Train models
    print("\n" + "=" * 70)
    print("TRAINING MODELS")
    print("=" * 70)
    
    # Random Forest
    rf_model, rf_accuracy, feature_importance = train_random_forest(
        X_train_scaled, X_test_scaled, y_train, y_test, scaler
    )
    
    # Gradient Boosting
    gb_model, gb_accuracy = train_gradient_boosting(
        X_train_scaled, X_test_scaled, y_train, y_test, scaler
    )
    
    # Choose best model
    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)
    print(f"Random Forest:     {rf_accuracy:.2%}")
    print(f"Gradient Boosting: {gb_accuracy:.2%}")
    
    if rf_accuracy >= gb_accuracy:
        best_model = rf_model
        best_accuracy = rf_accuracy
        best_name = "Random Forest"
    else:
        best_model = gb_model
        best_accuracy = gb_accuracy
        best_name = "Gradient Boosting"
    
    print(f"\n🏆 Best Model: {best_name} ({best_accuracy:.2%})")
    
    # Plot confusion matrix for best model
    y_pred = best_model.predict(X_test_scaled)
    plot_confusion_matrix(y_test, y_pred, best_name)
    
    # Save best model
    save_model(best_model, scaler, feature_columns, best_accuracy, best_name)
    
    # Plot feature importance if Random Forest won
    if best_name == "Random Forest":
        plt.figure(figsize=(10, 8))
        feature_importance.head(15).plot(x='feature', y='importance', kind='barh')
        plt.title('Top 15 Feature Importances')
        plt.xlabel('Importance')
        plt.tight_layout()
        plt.savefig('models/feature_importance.png')
        plt.close()
        print("✅ Saved feature importance: models/feature_importance.png")
    
    # Cleanup
    mt5.shutdown()
    
    print("\n" + "=" * 70)
    print("✅ TRAINING COMPLETE!")
    print("=" * 70)
    print(f"\n📁 Model saved to: {MODEL_SAVE_PATH}")
    print(f"🎯 Expected Accuracy: {best_accuracy:.2%}")
    print("\n⚡ Your trading bot will now use this model automatically!")
    print("🚀 Restart your bot to activate the new model.")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
