import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
from utils.logger import LOG_FILE

class DailyReport:
    def __init__(self, log_file=LOG_FILE):
        self.df = pd.read_csv(log_file, parse_dates=["DateTime"])

    def generate(self, day=None):
        if day is None:
            day = datetime.now().date()
        df_day = self.df[self.df["DateTime"].dt.date == day]
        if df_day.empty:
            return None

        trades = len(df_day)
        wins = len(df_day[df_day["Result"]=="TP"])
        losses = len(df_day[df_day["Result"]=="SL"])
        pnl = df_day["PnL_Percent"].sum()
        avg_ml = df_day["ML_Conf"].mean()

        df_day["Equity"] = df_day["PnL_Percent"].cumsum()
        plt.figure(figsize=(6,3))
        plt.plot(df_day["DateTime"], df_day["Equity"], marker="o")
        plt.title(f"Daily Equity Curve {day}")
        plt.xlabel("Time")
        plt.ylabel("Cumulative PnL %")
        plot_file = f"data/logs/equity_{day}.png"
        plt.savefig(plot_file)
        plt.close()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial","B",14)
        pdf.cell(0,10,f"Daily Trading Report {day}",0,1)
        pdf.set_font("Arial","",12)
        pdf.cell(0,8,f"Trades: {trades} | Wins: {wins} | Losses: {losses}",0,1)
        pdf.cell(0,8,f"Total PnL %: {pnl:.2f} | Avg ML Conf: {avg_ml:.2f}",0,1)
        pdf.image(plot_file, x=10, y=50, w=180)
        pdf_file = f"data/logs/daily_report_{day}.pdf"
        pdf.output(pdf_file)
        return pdf_file, trades, wins, losses, pnl, avg_ml
