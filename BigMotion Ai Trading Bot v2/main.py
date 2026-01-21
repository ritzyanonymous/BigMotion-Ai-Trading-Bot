"""
MT5 Auto-Trading Bot - ENHANCED with Multi-TP
Windows Compatible Version
"""
import os
import sys
import time
import signal
from datetime import datetime
from typing import List, Dict, Optional
import logging

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

from utils.logger import log_trade, update_trade_result
from utils.daily_report import DailyReport
from utils.telegram_report import send_telegram_message
from utils.config import Config
from utils.state_manager import StateManager
from utils.indicators import calculate_indicators
from utils.ml_predictor import MLPredictor
from utils.position_manager import PositionManager

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MT5TradingBot:
    """Enhanced MT5 Trading Bot with Multi-TP Strategy"""
    
    def __init__(self, config_path: str = 'config.json'):
        try:
            self.config = Config(config_path)
            self.state_manager = StateManager('bot_state.json')
            self.ml_predictor = MLPredictor(self.config.get('ml_model_path'))
            self.position_manager = PositionManager()
            
            self.running = True
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_trade_check = datetime.now()
            self.daily_report_sent = False
            
            self.setup_signal_handlers()
            self.initialize_mt5()
            
            logger.info("[OK] Enhanced MT5 Trading Bot initialized")
            logger.info(f"[TARGET] Multi-TP Strategy: {self.config.get('tp_splits')}")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def initialize_mt5(self):
        if not mt5.initialize():
            raise Exception(f"MT5 initialization failed: {mt5.last_error()}")
        
        login = self.config.get('mt5_login')
        password = self.config.get('mt5_password')
        server = self.config.get('mt5_server')
        
        if login and password and server:
            if not mt5.login(int(login), password, server):
                raise Exception(f"MT5 login failed: {mt5.last_error()}")
        
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"[CONNECTED] Account: {account_info.login}")
            logger.info(f"[BALANCE] {account_info.balance} {account_info.currency}")
    
    def shutdown(self, signum=None, frame=None):
        logger.info("[STOP] Shutting down trading bot...")
        self.running = False
        
        if self.daily_trades > 0 and not self.daily_report_sent:
            logger.info("Sending final report...")
            self.send_daily_report()
        
        mt5.shutdown()
        self.state_manager.save_state({
            'last_shutdown': datetime.now().isoformat(),
            'status': 'stopped'
        })
        logger.info("[OK] Bot stopped safely")
        sys.exit(0)
    
    def get_account_balance(self) -> float:
        account_info = mt5.account_info()
        return account_info.balance if account_info else 0.0
    
    def calculate_position_size(self, symbol: str, stop_loss_pips: float) -> float:
        balance = self.get_account_balance()
        risk_amount = balance * (self.config.risk_per_trade / 100)
        
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return 0.0
        
        pip_value = 0.01 if "JPY" in symbol else 0.0001
        lot_size = risk_amount / (stop_loss_pips * pip_value * symbol_info.trade_contract_size)
        
        lot_step = symbol_info.volume_step
        lot_size = round(lot_size / lot_step) * lot_step
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
        
        return lot_size
    
    def get_market_data(self, symbol: str, timeframe: str = "H1", bars: int = 200) -> Optional[pd.DataFrame]:
        try:
            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe, mt5.TIMEFRAME_H1), 0, bars)
            
            if rates is None or len(rates) == 0:
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def analyze_market(self, symbol: str) -> Optional[Dict]:
        try:
            df = self.get_market_data(symbol, "H1", 200)
            if df is None or len(df) < 100:
                return None
            
            indicators = calculate_indicators(df)
            if indicators is None:
                return None
            
            current = {
                'close': df['close'].iloc[-1],
                'ema_20': indicators['ema_20'].iloc[-1],
                'ema_50': indicators['ema_50'].iloc[-1],
                'ema_200': indicators['ema_200'].iloc[-1],
                'rsi': indicators['rsi'].iloc[-1],
                'adx': indicators['adx'].iloc[-1],
                'atr': indicators['atr'].iloc[-1],
            }
            
            if current['ema_20'] > current['ema_50'] > current['ema_200']:
                trend = "Bull"
            elif current['ema_20'] < current['ema_50'] < current['ema_200']:
                trend = "Bear"
            else:
                trend = "Sideways"
            
            ml_features = self.prepare_ml_features(df, indicators)
            ml_confidence, ml_signal = self.ml_predictor.predict(ml_features)
            
            signal = self.generate_signal(current, trend, ml_confidence, ml_signal)
            
            if signal:
                signal.update({
                    'symbol': symbol,
                    'atr': current['atr'],
                    'rsi': current['rsi'],
                    'adx': current['adx'],
                    'trend': trend,
                    'ml_confidence': ml_confidence
                })
            
            return signal
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def prepare_ml_features(self, df: pd.DataFrame, indicators: pd.DataFrame) -> np.ndarray:
        """Prepare all 18 features for ML model"""
        try:
            # Get latest values
            latest = df.iloc[-1]
            latest_ind = indicators.iloc[-1]
            
            # Create feature array matching training (18 features)
            features = [
                latest_ind['rsi'],              # 0
                latest_ind['adx'],              # 1
                latest_ind['atr'],              # 2
                latest_ind['ema_20'],           # 3
                latest_ind['ema_50'],           # 4
                latest_ind['ema_200'],          # 5
                latest_ind['macd'],             # 6
                latest_ind['macd_signal'],      # 7
                latest_ind['macd_histogram'],   # 8
                latest_ind['bb_position'],      # 9
                latest_ind['trend_bull'],       # 10
                latest_ind['trend_bear'],       # 11
                latest_ind['price_change'],     # 12
                latest_ind['volatility'],       # 13
                datetime.now().hour,            # 14
                datetime.now().weekday(),       # 15
                latest['close'],                # 16
                latest['tick_volume']           # 17
            ]
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Error preparing ML features: {e}")
            return None
    
    def generate_signal(self, current: Dict, trend: str, ml_confidence: float, ml_signal: str) -> Optional[Dict]:
        if ml_confidence < self.config.min_ml_confidence or current['adx'] < 20:
            return None
        
        if trend == "Bull" and ml_signal == "BUY" and 40 < current['rsi'] < 70:
            entry = current['close']
            atr = current['atr']
            sl = entry - (2 * atr)
            tp_final = entry + (3.75 * atr)
            
            tp_range = tp_final - entry
            return {
                'direction': 'BUY',
                'entry_price': entry,
                'sl': sl,
                'tp_levels': [
                    entry + (tp_range * 0.30),
                    entry + (tp_range * 0.60),
                    tp_final
                ],
                'reason': 'Trend+ML Signal'
            }
        
        elif trend == "Bear" and ml_signal == "SELL" and 30 < current['rsi'] < 60:
            entry = current['close']
            atr = current['atr']
            sl = entry + (2 * atr)
            tp_final = entry - (3.75 * atr)
            
            tp_range = abs(entry - tp_final)
            return {
                'direction': 'SELL',
                'entry_price': entry,
                'sl': sl,
                'tp_levels': [
                    entry - (tp_range * 0.30),
                    entry - (tp_range * 0.60),
                    tp_final
                ],
                'reason': 'Trend+ML Signal'
            }
        
        return None
    
    def check_risk_limits(self) -> bool:
        if self.daily_trades >= self.config.max_trades_per_day:
            logger.warning(f"[LIMIT] Daily trade limit reached: {self.daily_trades}/{self.config.max_trades_per_day}")
            return False
        
        if self.daily_pnl <= -self.config.max_daily_loss:
            logger.warning(f"[STOP] Daily loss limit: {self.daily_pnl:.2f}%")
            send_telegram_message(
                self.config.telegram_token,
                self.config.telegram_chat_id,
                f"🛑 TRADING STOPPED\n━━━━━━━━━━━━━━━━\nDaily loss limit reached: {self.daily_pnl:.2f}%\nBot will resume tomorrow."
            )
            return False
        
        if mt5.positions_total() >= self.config.max_open_positions:
            return False
        
        return True
    
    def execute_multi_tp_trade(self, signal: Dict) -> bool:
        """Execute trade with 3 TP levels"""
        try:
            symbol = signal['symbol']
            direction = signal['direction']
            sl = signal['sl']
            tp_levels = signal['tp_levels']
            
            logger.info(f"[EXEC] Attempting to execute {direction} on {symbol}")
            
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"[ERROR] Symbol {symbol} not found")
                return False
            
            if not symbol_info.visible:
                logger.info(f"[INFO] Making {symbol} visible in Market Watch")
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"[ERROR] Failed to select {symbol}")
                    return False
            
            pip_divisor = 0.01 if "JPY" in symbol else 0.0001
            stop_loss_pips = abs(signal['entry_price'] - sl) / pip_divisor
            total_lot = self.calculate_position_size(symbol, stop_loss_pips)
            
            logger.info(f"[CALC] Calculated lot size: {total_lot} (min: {symbol_info.volume_min})")
            
            if total_lot < symbol_info.volume_min:
                logger.warning(f"[SKIP] Lot size {total_lot} too small (min: {symbol_info.volume_min})")
                return False
            
            # Split lots: 40%, 30%, 30%
            tp_splits = self.config.get('tp_splits', [0.40, 0.30, 0.30])
            lot_splits = [round(total_lot * split / symbol_info.volume_step) * symbol_info.volume_step 
                         for split in tp_splits]
            lot_splits[-1] = total_lot - sum(lot_splits[:-1])
            
            logger.info(f"[SPLIT] Lots split into: {lot_splits}")
            
            order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).ask if direction == "BUY" else mt5.symbol_info_tick(symbol).bid
            
            logger.info(f"[PRICE] Entry price: {price}, SL: {sl}, TPs: {tp_levels}")
            
            orders_placed = []
            
            for i, (lot, tp) in enumerate(zip(lot_splits, tp_levels)):
                if lot < symbol_info.volume_min:
                    logger.warning(f"[SKIP] TP{i+1} lot {lot} below minimum {symbol_info.volume_min}")
                    continue
                
                logger.info(f"[ORDER] Sending TP{i+1} order: {lot} lot @ TP={tp}")
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": order_type,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "deviation": 20,
                    "magic": 234000 + i,
                    "comment": f"AI_TP{i+1}",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    orders_placed.append({
                        'ticket': result.order,
                        'tp_level': i + 1,
                        'lot': lot,
                        'tp': tp
                    })
                    logger.info(f"[OK] TP{i+1} placed: {lot} lot @ {tp}")
                else:
                    logger.error(f"[FAILED] TP{i+1} order failed: {result.retcode} - {result.comment}")
            
            if not orders_placed:
                logger.error("[FAILED] No orders placed successfully")
                return False
            
            self.daily_trades += 1
            
            # Calculate pips for display
            sl_pips = abs(price - sl) / pip_divisor
            tp_pips = [(abs(tp - price) / pip_divisor) for tp in tp_levels]
            
            # Log trade
            log_trade(
                Symbol=symbol,
                Direction=direction,
                Lot=total_lot,
                EntryPrice=price,
                SL=sl,
                TP=tp_levels[2],
                ATR=signal['atr'],
                EMA_Trend=signal['trend'],
                RSI=signal['rsi'],
                ADX=signal['adx'],
                ML_Conf=signal['ml_confidence'],
                Spread=symbol_info.spread * symbol_info.point,
                Reason=signal['reason'],
                Result="OPEN",
                PnL_Percent=0.0,
                Notes=f"MultiTP:{len(orders_placed)}"
            )
            
            # Track positions
            for order in orders_placed:
                self.position_manager.add_position(
                    order['ticket'],
                    symbol,
                    direction,
                    order['lot'],
                    price,
                    sl,
                    order['tp'],
                    order['tp_level']
                )
            
            # Telegram notification (emojis work in Telegram!)
            msg = (
                f"🤖 TRADE OPENED\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"Symbol: {symbol}\n"
                f"Direction: {direction}\n"
                f"Total Lot: {total_lot}\n"
                f"Entry: {price}\n\n"
                f"🎯 Multiple Take Profits:\n"
                f"TP1 ({int(tp_splits[0]*100)}%): {tp_levels[0]:.5f} [+{tp_pips[0]:.1f} pips]\n"
                f"TP2 ({int(tp_splits[1]*100)}%): {tp_levels[1]:.5f} [+{tp_pips[1]:.1f} pips]\n"
                f"TP3 ({int(tp_splits[2]*100)}%): {tp_levels[2]:.5f} [+{tp_pips[2]:.1f} pips]\n"
                f"SL: {sl:.5f} [-{sl_pips:.1f} pips]\n\n"
                f"ML Confidence: {signal['ml_confidence']:.2f}"
            )
            
            send_telegram_message(
                self.config.telegram_token,
                self.config.telegram_chat_id,
                msg
            )
            
            logger.info(f"[TRADE] Multi-TP opened: {symbol} {direction}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def monitor_positions(self):
        """Monitor and detect closed positions"""
        try:
            closed = self.position_manager.check_closed_positions()
            
            for pos in closed:
                # Update log
                update_trade_result(
                    pos['symbol'],
                    pos['close_time'],
                    pos['result'],
                    pos['pnl_percent']
                )
                
                # Update daily PnL
                self.daily_pnl += pos['pnl_percent']
                
                # Notification (emojis work in Telegram!)
                emoji = "✅" if pos['result'] == 'TP' else "❌"
                result_text = f"TP{pos['tp_level']} HIT" if pos['result'] == 'TP' else "STOP LOSS"
                
                msg = (
                    f"{emoji} {result_text} - {pos['symbol']}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Closed: {pos['lot']} lot\n"
                    f"Profit: {pos['pnl_percent']:+.2f}%"
                )
                
                remaining = self.position_manager.get_open_positions_for_symbol(pos['symbol'])
                if remaining:
                    msg += f"\nRemaining: {len(remaining)} position(s) running"
                else:
                    total_pnl = self.position_manager.get_total_pnl_for_symbol(pos['symbol'])
                    msg = (
                        f"🎉 TRADE FULLY CLOSED - {pos['symbol']}\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"Total Profit: {total_pnl:+.2f}%"
                    )
                
                send_telegram_message(
                    self.config.telegram_token,
                    self.config.telegram_chat_id,
                    msg
                )
                
                logger.info(f"[CLOSED] {pos['symbol']} - {pos['result']} - {pos['pnl_percent']:+.2f}%")
                
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def reset_daily_counters(self):
        now = datetime.now()
        if now.date() > self.last_trade_check.date():
            logger.info("[NEW DAY] Resetting counters")
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.daily_report_sent = False
            self.last_trade_check = now
            self.position_manager.reset_daily_tracking()
    
    def scan_and_trade(self):
        try:
            if not self.check_risk_limits():
                return
            
            for symbol in self.config.get('trading_pairs', []):
                if not self.check_risk_limits():
                    break
                
                if self.position_manager.has_open_positions(symbol):
                    continue
                
                signal = self.analyze_market(symbol)
                if signal:
                    logger.info(f"[SIGNAL] {symbol} {signal['direction']}")
                    self.execute_multi_tp_trade(signal)
                    time.sleep(2)
                    
        except Exception as e:
            logger.error(f"Error in scan_and_trade: {e}")
    
    def send_daily_report(self):
        try:
            daily = DailyReport()
            pdf_file, stats = daily.generate()
            
            if pdf_file and stats:
                # Telegram message with emojis
                msg = (
                    f"📊 DAILY SUMMARY\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"Trades: {stats['total_trades']}\n"
                    f"Wins: {stats['wins']} | Losses: {stats['losses']}\n"
                    f"Win Rate: {stats['win_rate']:.1f}%\n"
                    f"Total PnL: {stats['total_pnl']:+.2f}%\n\n"
                    f"📄 Detailed PDF report attached"
                )
                
                send_telegram_message(
                    self.config.telegram_token,
                    self.config.telegram_chat_id,
                    msg,
                    pdf_file
                )
                
                self.daily_report_sent = True
                logger.info("[REPORT] Daily report sent")
                
        except Exception as e:
            logger.error(f"Error sending report: {e}")
    
    def check_report_time(self):
        now = datetime.now()
        if now.hour >= 17 and self.daily_trades > 0 and not self.daily_report_sent:
            self.send_daily_report()
    
    def run(self):
        logger.info("[START] Enhanced MT5 Bot starting...")
        logger.info(f"[PAIRS] {self.config.get('trading_pairs')}")
        logger.info(f"[RISK] {self.config.risk_per_trade}% per trade")
        logger.info(f"[MULTI-TP] {self.config.get('tp_splits')}")
        
        # Telegram notification (emojis work here!)
        send_telegram_message(
            self.config.telegram_token,
            self.config.telegram_chat_id,
            "🤖 Enhanced MT5 Bot Started!\n✅ Multi-TP Strategy Active\n✅ Ready to trade"
        )
        
        while self.running:
            try:
                self.reset_daily_counters()
                self.monitor_positions()
                self.scan_and_trade()
                self.check_report_time()
                time.sleep(self.config.loop_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                time.sleep(30)


def main():
    try:
        bot = MT5TradingBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
