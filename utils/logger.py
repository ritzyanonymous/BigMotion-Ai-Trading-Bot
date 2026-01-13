import csv, os
from datetime import datetime

LOG_FILE = "data/logs/trades.csv"

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "DateTime", "Symbol", "Direction", "Lot", "EntryPrice",
            "SL", "TP", "ATR", "EMA_Trend", "RSI", "ADX", "ML_Conf",
            "Spread", "Reason", "Result", "PnL_Percent", "Notes"
        ])

def log_trade(**kwargs):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = [now] + [kwargs.get(k, "") for k in [
        "Symbol","Direction","Lot","EntryPrice","SL","TP","ATR",
        "EMA_Trend","RSI","ADX","ML_Conf","Spread","Reason",
        "Result","PnL_Percent","Notes"
    ]]
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)
