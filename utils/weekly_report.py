import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import matplotlib.pyplot as plt
from utils.logger import LOG_FILE

class WeeklyReport:
    def __init__(self, log_file=LOG_FILE):
        self.df = pd.read_csv(log_file, parse_dates=["DateTime"])

    def generate(self):
        last_monday = datetime.now() - timedelta(days=datetime.now().weekday())
        df_week = self.df[self.df["DateTime"].dt.date >= last_monday.date()]
        if df_week.empty:
            return None

        summary = df_week.groupby("Symbol").agg({
            "Result": lambda x: (x=="TP").sum(),
            "PnL_Percent": "sum",
            "ML_Conf": "mean"
        }).rename(columns={"Result":"Wins"})

        df_week = df_week.sort_values("DateTime")
        df_week["Equity"] = df_week["PnL_Percent"].cumsum()
        plt.figure(figsize=(6,3))
        plt.plot(df_week["DateTime"], df_week["Equity"], marker="o")
        plt.title("Weekly Equity Curve")
        plt.xlabel("Date")
        plt.ylabel("Cumulative PnL %")
        plot_file = "data/logs/equity_week.png"
        plt.savefig(plot_file)
        plt.close()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial","B",14)
        pdf.cell(0,10,"Weekly Trading Report",0,1)
        pdf.set_font("Arial","",12)
        for sym in summary.index:
            pdf.cell(0,8,f"{sym} | Wins: {summary.loc[sym,'Wins']} | PnL %: {summary.loc[sym,'PnL_Percent']:.2f} | Avg ML Conf: {summary.loc[sym,'ML_Conf']:.2f}",0,1)
        pdf.image(plot_file,x=10,y=60,w=180)
        pdf_file = "data/logs/weekly_report.pdf"
        pdf.output(pdf_file)
        return pdf_file, summary
