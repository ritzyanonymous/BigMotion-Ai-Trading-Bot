import time
from datetime import datetime
from utils.logger import log_trade
from utils.daily_report import DailyReport
from utils.weekly_report import WeeklyReport
from utils.telegram_report import send_telegram_message

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

last_daily_report_day = None
last_weekly_report_week = None

def run_trading_logic():
    trades = [
        {"Symbol":"EURUSD","Direction":"BUY","Lot":0.1,"EntryPrice":1.0890,"SL":1.0850,"TP":1.0925,"ATR":0.0012,"EMA_Trend":"Bull","RSI":55,"ADX":25,"ML_Conf":0.67,"Spread":0.00018,"Reason":"Trend+Pullback","Result":"TP","PnL_Percent":0.9,"Notes":""},
        {"Symbol":"GBPUSD","Direction":"SELL","Lot":0.1,"EntryPrice":1.3020,"SL":1.3060,"TP":1.2980,"ATR":0.0015,"EMA_Trend":"Bear","RSI":48,"ADX":28,"ML_Conf":0.70,"Spread":0.00020,"Reason":"Trend+ML Signal","Result":"SL","PnL_Percent":-0.9,"Notes":""},
        {"Symbol":"USDJPY","Direction":"BUY","Lot":0.1,"EntryPrice":134.50,"SL":134.20,"TP":134.85,"ATR":0.15,"EMA_Trend":"Bull","RSI":60,"ADX":30,"ML_Conf":0.65,"Spread":0.02,"Reason":"Trend+ML Signal","Result":"TP","PnL_Percent":1.0,"Notes":""}
    ]
    return trades

while True:
    trades = run_trading_logic()
    for trade in trades:
        log_trade(**trade)

    now = datetime.now()

    if last_daily_report_day != now.date():
        daily = DailyReport()
        pdf_file, trades_num, wins, losses, pnl, avg_ml = daily.generate()
        if pdf_file:
            msg = f"📊 Daily Report {now.date()}\nTrades: {trades_num} | Wins: {wins} | Losses: {losses}\nTotal PnL %: {pnl:.2f} | Avg ML Conf: {avg_ml:.2f}"
            send_telegram_message(BOT_TOKEN, CHAT_ID, msg, pdf_file)
        last_daily_report_day = now.date()

    current_week = now.isocalendar()[1]
    if last_weekly_report_week != current_week and now.weekday()==6:
        weekly = WeeklyReport()
        pdf_file, summary = weekly.generate()
        if pdf_file:
            send_telegram_message(BOT_TOKEN, CHAT_ID, f"📊 Weekly Report Week {current_week}", pdf_file)
        last_weekly_report_week = current_week

    time.sleep(60)
