"""
Enhanced Daily Report Generator
Generates ONE comprehensive PDF at end of day
"""
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import logging

logger = logging.getLogger(__name__)


class DailyReport:
    def __init__(self):
        self.log_file = "data/logs/trades.csv"
        self.report_dir = "reports"
        os.makedirs(self.report_dir, exist_ok=True)
    
    def generate(self):
        """Generate comprehensive daily PDF report"""
        try:
            if not os.path.exists(self.log_file):
                logger.warning(f"Trade log file not found: {self.log_file}")
                return None, None
            
            df = pd.read_csv(self.log_file)
            if df.empty:
                logger.info("No trades in log file")
                return None, None
            
            df['DateTime'] = pd.to_datetime(df['DateTime'])
            today = datetime.now().date()
            today_trades = df[df['DateTime'].dt.date == today]
            
            if today_trades.empty:
                logger.info("No trades today")
                return None, None
            
            # Calculate statistics
            closed_trades = today_trades[today_trades['Result'].isin(['TP', 'SL'])]
            
            total_trades = len(today_trades)
            wins = len(closed_trades[closed_trades['Result'] == 'TP'])
            losses = len(closed_trades[closed_trades['Result'] == 'SL'])
            open_trades = len(today_trades[today_trades['Result'] == 'OPEN'])
            
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            total_pnl = closed_trades['PnL_Percent'].sum() if not closed_trades.empty else 0.0
            avg_ml = today_trades['ML_Conf'].mean()
            
            # Best and worst trades
            if not closed_trades.empty:
                best_trade = closed_trades.loc[closed_trades['PnL_Percent'].idxmax()]
                worst_trade = closed_trades.loc[closed_trades['PnL_Percent'].idxmin()]
            else:
                best_trade = None
                worst_trade = None
            
            # Create equity curve chart
            chart_file = None
            if not closed_trades.empty:
                closed_sorted = closed_trades.sort_values('DateTime')
                closed_sorted['Cumulative_PnL'] = closed_sorted['PnL_Percent'].cumsum()
                
                plt.figure(figsize=(8, 4))
                plt.plot(closed_sorted['DateTime'], closed_sorted['Cumulative_PnL'], 
                        marker='o', linewidth=2, markersize=6)
                plt.axhline(y=0, color='r', linestyle='--', alpha=0.5)
                plt.title(f'Daily Equity Curve - {today}', fontsize=14, fontweight='bold')
                plt.xlabel('Time')
                plt.ylabel('Cumulative PnL (%)')
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                chart_file = f"{self.report_dir}/daily_chart_{today}.png"
                plt.savefig(chart_file, dpi=150)
                plt.close()
            
            # Generate PDF
            pdf_file = f"{self.report_dir}/daily_report_{today}.pdf"
            c = canvas.Canvas(pdf_file, pagesize=letter)
            width, height = letter
            
            # === PAGE 1: SUMMARY ===
            y_pos = height - 0.75*inch
            
            # Title
            c.setFont("Helvetica-Bold", 24)
            c.drawString(1*inch, y_pos, f"Daily Trading Report")
            y_pos -= 0.3*inch
            c.setFont("Helvetica", 14)
            c.drawString(1*inch, y_pos, f"{today.strftime('%A, %B %d, %Y')}")
            y_pos -= 0.6*inch
            
            # Performance Box
            c.setStrokeColor(colors.HexColor('#2196F3'))
            c.setLineWidth(2)
            c.rect(0.75*inch, y_pos - 2.5*inch, width - 1.5*inch, 2.5*inch)
            
            c.setFont("Helvetica-Bold", 16)
            c.drawString(1*inch, y_pos - 0.3*inch, "PERFORMANCE SUMMARY")
            
            y_pos -= 0.7*inch
            c.setFont("Helvetica", 12)
            
            # Summary stats
            summary_data = [
                f"Total Trades: {total_trades}",
                f"Closed: {wins + losses} | Open: {open_trades}",
                f"Wins: {wins} | Losses: {losses}",
                f"Win Rate: {win_rate:.1f}%",
                f"Total PnL: {total_pnl:+.2f}%",
                f"Avg ML Confidence: {avg_ml:.2f}"
            ]
            
            for line in summary_data:
                c.drawString(1.2*inch, y_pos, line)
                y_pos -= 0.25*inch
            
            y_pos -= 0.5*inch
            
            # Best/Worst trades
            if best_trade is not None:
                c.setFont("Helvetica-Bold", 14)
                c.drawString(1*inch, y_pos, "Best Trade")
                y_pos -= 0.25*inch
                c.setFont("Helvetica", 11)
                c.drawString(1.2*inch, y_pos, 
                    f"{best_trade['Symbol']} {best_trade['Direction']} - {best_trade['Result']} - PnL: +{best_trade['PnL_Percent']:.2f}%")
                y_pos -= 0.4*inch
                
                c.setFont("Helvetica-Bold", 14)
                c.drawString(1*inch, y_pos, "Worst Trade")
                y_pos -= 0.25*inch
                c.setFont("Helvetica", 11)
                c.drawString(1.2*inch, y_pos,
                    f"{worst_trade['Symbol']} {worst_trade['Direction']} - {worst_trade['Result']} - PnL: {worst_trade['PnL_Percent']:.2f}%")
                y_pos -= 0.5*inch
            
            # Chart
            if chart_file and os.path.exists(chart_file):
                c.drawImage(chart_file, 0.75*inch, y_pos - 3*inch, 
                           width=6.5*inch, height=2.8*inch)
                y_pos -= 3.2*inch
            
            # === PAGE 2: TRADE DETAILS ===
            c.showPage()
            y_pos = height - 0.75*inch
            
            c.setFont("Helvetica-Bold", 18)
            c.drawString(1*inch, y_pos, "TRADE DETAILS")
            y_pos -= 0.5*inch
            
            c.setFont("Helvetica", 10)
            
            for idx, trade in today_trades.iterrows():
                if y_pos < 1.5*inch:
                    c.showPage()
                    y_pos = height - 1*inch
                
                result_marker = "[WIN]" if trade['Result'] == 'TP' else "[LOSS]" if trade['Result'] == 'SL' else "[OPEN]"
                
                c.setFont("Helvetica-Bold", 11)
                c.drawString(1*inch, y_pos, 
                    f"{result_marker} {trade['Symbol']} - {trade['Direction']}")
                
                y_pos -= 0.2*inch
                c.setFont("Helvetica", 9)
                
                details = [
                    f"  Entry: {trade['EntryPrice']} | SL: {trade['SL']} | TP: {trade['TP']}",
                    f"  Lot: {trade['Lot']} | Spread: {trade['Spread']}",
                    f"  Indicators: RSI={trade['RSI']:.0f} | ADX={trade['ADX']:.0f} | ATR={trade['ATR']:.5f}",
                    f"  ML Confidence: {trade['ML_Conf']:.2f} | Trend: {trade['EMA_Trend']}",
                    f"  Result: {trade['Result']} | PnL: {trade['PnL_Percent']:.2f}%",
                    f"  Reason: {trade['Reason']} | Notes: {trade['Notes']}"
                ]
                
                for detail in details:
                    c.drawString(1*inch, y_pos, detail)
                    y_pos -= 0.18*inch
                
                y_pos -= 0.15*inch
                c.setStrokeColor(colors.grey)
                c.line(1*inch, y_pos, width - 1*inch, y_pos)
                y_pos -= 0.2*inch
            
            c.save()
            
            logger.info(f"Daily report generated: {pdf_file}")
            
            # Return stats for Telegram
            stats = {
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'total_pnl': total_pnl
            }
            
            return pdf_file, stats
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            import traceback
            traceback.print_exc()
            return None, None
