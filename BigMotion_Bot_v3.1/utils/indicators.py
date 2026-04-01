"""
Complete Technical Indicators Module
Calculates all 18 features needed for ML model
"""
import pandas as pd
import numpy as np


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high, low, close = df['high'], df['low'], df['close']
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average Directional Index"""
    high, low, close = df['high'], df['low'], df['close']
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(window=period).mean()


def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
    """Calculate Bollinger Bands"""
    sma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return {
        'upper': upper_band,
        'middle': sma,
        'lower': lower_band
    }


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators needed for ML model
    Returns DataFrame with all 18+ indicators
    """
    try:
        indicators = pd.DataFrame(index=df.index)
        
        # EMAs (Features 3, 4, 5)
        indicators['ema_20'] = calculate_ema(df['close'], 20)
        indicators['ema_50'] = calculate_ema(df['close'], 50)
        indicators['ema_200'] = calculate_ema(df['close'], 200)
        
        # RSI (Feature 0)
        indicators['rsi'] = calculate_rsi(df['close'], 14)
        
        # ATR (Feature 2)
        indicators['atr'] = calculate_atr(df, 14)
        
        # ADX (Feature 1)
        indicators['adx'] = calculate_adx(df, 14)
        
        # MACD (Features 6, 7, 8)
        macd = calculate_macd(df['close'])
        indicators['macd'] = macd['macd']
        indicators['macd_signal'] = macd['signal']
        indicators['macd_histogram'] = macd['histogram']
        
        # Bollinger Bands (Feature 9 - bb_position)
        bb = calculate_bollinger_bands(df['close'])
        indicators['bb_upper'] = bb['upper']
        indicators['bb_middle'] = bb['middle']
        indicators['bb_lower'] = bb['lower']
        
        # BB Position: where price is within bands (0=lower, 0.5=middle, 1=upper)
        bb_range = indicators['bb_upper'] - indicators['bb_lower']
        bb_range = bb_range.replace(0, 1)  # Avoid division by zero
        indicators['bb_position'] = (df['close'] - indicators['bb_lower']) / bb_range
        indicators['bb_position'] = indicators['bb_position'].clip(0, 1)  # Keep between 0 and 1
        
        # Trend indicators (Features 10, 11)
        indicators['trend_bull'] = (
            (indicators['ema_20'] > indicators['ema_50']) & 
            (indicators['ema_50'] > indicators['ema_200'])
        ).astype(float)
        
        indicators['trend_bear'] = (
            (indicators['ema_20'] < indicators['ema_50']) & 
            (indicators['ema_50'] < indicators['ema_200'])
        ).astype(float)
        
        # Price action (Features 12, 13)
        indicators['price_change'] = df['close'].pct_change()
        indicators['volatility'] = indicators['price_change'].rolling(window=20).std()
        
        # Fill NaN values (pandas 2.0+ compatible)
        indicators = indicators.bfill().fillna(0)
        
        return indicators
        
    except Exception as e:
        print(f"Error calculating indicators: {e}")
        return None


def get_trend_strength(adx: float) -> str:
    """Determine trend strength based on ADX value"""
    if adx < 20:
        return "Weak/No Trend"
    elif adx < 40:
        return "Moderate Trend"
    else:
        return "Strong Trend"


def get_rsi_signal(rsi: float) -> str:
    """Get RSI signal"""
    if rsi < 30:
        return "Oversold"
    elif rsi > 70:
        return "Overbought"
    else:
        return "Neutral"


def get_macd_signal(macd: float, signal: float) -> str:
    """Get MACD signal"""
    if macd > signal:
        return "Bullish"
    elif macd < signal:
        return "Bearish"
    else:
        return "Neutral"
