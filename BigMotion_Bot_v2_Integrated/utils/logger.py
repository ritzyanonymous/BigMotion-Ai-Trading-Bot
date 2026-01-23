"""
Enhanced Trade Logger with Update Capability
"""
import csv
import os
import pandas as pd
from datetime import datetime
from typing import Optional

LOG_FILE = "data/logs/trades.csv"

# Ensure log file exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "DateTime", "Symbol", "Direction", "Lot", "EntryPrice",
            "SL", "TP", "ATR", "EMA_Trend", "RSI", "ADX", "ML_Conf",
            "Spread", "Reason", "Result", "PnL_Percent", "Notes"
        ])


def log_trade(**kwargs):
    """Log a new trade"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = [now] + [kwargs.get(k, "") for k in [
        "Symbol","Direction","Lot","EntryPrice","SL","TP","ATR",
        "EMA_Trend","RSI","ADX","ML_Conf","Spread","Reason",
        "Result","PnL_Percent","Notes"
    ]]
    
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def update_trade_result(symbol: str, close_time: datetime, result: str, pnl_percent: float):
    """Update trade result when position closes"""
    try:
        # Read existing trades
        df = pd.read_csv(LOG_FILE)
        
        # Find the most recent OPEN trade for this symbol
        mask = (df['Symbol'] == symbol) & (df['Result'] == 'OPEN')
        
        if mask.any():
            # Get the last matching index
            idx = df[mask].index[-1]
            
            # Update the trade
            df.at[idx, 'Result'] = result
            df.at[idx, 'PnL_Percent'] = pnl_percent
            
            # Add close time to Notes
            close_time_str = close_time.strftime("%Y-%m-%d %H:%M")
            current_notes = df.at[idx, 'Notes']
            df.at[idx, 'Notes'] = f"{current_notes} | Closed: {close_time_str}"
            
            # Save back to CSV
            df.to_csv(LOG_FILE, index=False)
            
            return True
        
        return False
        
    except Exception as e:
        print(f"Error updating trade result: {e}")
        return False


def get_today_trades() -> pd.DataFrame:
    """Get all trades from today"""
    try:
        df = pd.read_csv(LOG_FILE)
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        today = datetime.now().date()
        return df[df['DateTime'].dt.date == today]
    except Exception as e:
        print(f"Error getting today's trades: {e}")
        return pd.DataFrame()


def get_trade_statistics(days: int = 1) -> dict:
    """Get trading statistics for last N days"""
    try:
        df = pd.read_csv(LOG_FILE)
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        cutoff = datetime.now() - pd.Timedelta(days=days)
        recent = df[df['DateTime'] >= cutoff]
        
        # Filter only closed trades
        closed = recent[recent['Result'].isin(['TP', 'SL'])]
        
        if closed.empty:
            return {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
        
        wins = closed[closed['Result'] == 'TP']
        losses = closed[closed['Result'] == 'SL']
        
        return {
            'total_trades': len(closed),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': (len(wins) / len(closed) * 100) if len(closed) > 0 else 0,
            'total_pnl': closed['PnL_Percent'].sum(),
            'avg_win': wins['PnL_Percent'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['PnL_Percent'].mean() if len(losses) > 0 else 0
        }
        
    except Exception as e:
        print(f"Error calculating statistics: {e}")
        return {}
