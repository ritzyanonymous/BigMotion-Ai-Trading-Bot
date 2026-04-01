"""
MT5 Auto-Trading Bot - ENHANCED with Multi-TP
Windows Compatible Version
WITH: Comprehensive Logging, Startup Diagnostics, Health Monitoring
"""
import os
import sys
import time
import signal
from datetime import datetime
from typing import List, Dict, Optional
import logging
import traceback

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging with UTF-8 encoding - BEFORE any other imports
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("=" * 70)
logger.info("🤖 MT5 TRADING BOT STARTING")
logger.info(f"📅 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"🖥️  Platform: {sys.platform}")
logger.info(f"🐍 Python: {sys.version}")
logger.info("=" * 70)

# Import with error handling
try:
    logger.info("📦 Loading dependencies...")
    
    import MetaTrader5 as mt5
    logger.info("   ✅ MetaTrader5")
    
    import pandas as pd
    logger.info("   ✅ pandas")
    
    import numpy as np
    logger.info("   ✅ numpy")
    
    from utils.logger import log_trade, update_trade_result
    logger.info("   ✅ utils.logger")
    
    from utils.daily_report import DailyReport
    logger.info("   ✅ utils.daily_report")
    
    from utils.telegram_report import send_telegram_message
    logger.info("   ✅ utils.telegram_report")
    
    from utils.config import Config
    logger.info("   ✅ utils.config")
    
    from utils.state_manager import StateManager
    logger.info("   ✅ utils.state_manager")
    
    from utils.indicators import calculate_indicators
    logger.info("   ✅ utils.indicators")
    
    from utils.ml_predictor import MLPredictor
    logger.info("   ✅ utils.ml_predictor")
    
    from utils.position_manager import PositionManager
    logger.info("   ✅ utils.position_manager")
    
    from utils.diagnostics import run_diagnostics
    logger.info("   ✅ utils.diagnostics")
    
    from utils.health_check import MT5HealthCheck, create_health_monitor
    logger.info("   ✅ utils.health_check")
    
    from utils.license_client_v2 import check_license_on_startup
    logger.info("   ✅ utils.license_client_v2")
    
    logger.info("📦 All dependencies loaded successfully!")
    
except ImportError as e:
    logger.critical(f"❌ FATAL: Failed to import required module: {e}")
    logger.critical(f"   Traceback: {traceback.format_exc()}")
    logger.critical("   Please run: pip install -r requirements.txt")
    sys.exit(1)


class MT5TradingBot:
    """Enhanced MT5 Trading Bot with Multi-TP Strategy, Diagnostics, and Health Monitoring"""
    
    def __init__(self, config_path: str = 'config.json'):
        logger.info("-" * 50)
        logger.info("🔧 INITIALIZING BOT COMPONENTS")
        logger.info("-" * 50)
        
        try:
            # Step 0: Verify License (NEW - FIRST CHECK!)
            logger.info("Step 0/8: Verifying license...")
            
            # Get license server URL from config or use default
            import json
            try:
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                server_url = cfg.get('license_server_url', 'https://license.yourdomain.com')
            except:
                server_url = 'https://license.yourdomain.com'
            
            # Check license (handles trial, activation, everything!)
            is_valid, self.license_client = check_license_on_startup(server_url)
            
            if not is_valid:
                logger.critical("❌ License verification failed - exiting")
                raise Exception("License verification failed")
            
            logger.info("   ✅ License verified")
            logger.info(f"   🏆 License Tier: {self.license_client.license_tier}")
            if self.license_client.is_trial:
                logger.info(f"   🎯 Trial Mode: {self.license_client.trial_days_remaining} days remaining")
            
            # Step 1: Run startup diagnostics
            logger.info("Step 1/8: Running startup diagnostics...")
            diag_passed, diag_results = run_diagnostics(config_path)
            
            if not diag_passed:
                logger.critical("❌ Critical diagnostics failed!")
                for error in diag_results.get('errors', []):
                    logger.critical(f"   • {error['check']}: {error['message']}")
                raise Exception("Startup diagnostics failed - see errors above")
            
            logger.info("✅ Startup diagnostics passed")
            
            # Step 2: Load configuration
            logger.info("Step 2/8: Loading configuration...")
            self.config = Config(config_path)
            logger.info(f"   ✅ Config loaded from {config_path}")
            logger.info(f"   📊 Trading pairs: {self.config.get('trading_pairs')}")
            logger.info(f"   💰 Risk per trade: {self.config.risk_per_trade}%")
            logger.info(f"   🎯 TP splits: {self.config.get('tp_splits')}")
            
            # Step 3: Initialize state manager
            logger.info("Step 3/8: Initializing state manager...")
            self.state_manager = StateManager('bot_state.json')
            logger.info("   ✅ State manager ready")
            
            # Step 4: Load ML predictor
            logger.info("Step 4/8: Loading ML predictor...")
            ml_path = self.config.get('ml_model_path', 'models/trading_model.pkl')
            self.ml_predictor = MLPredictor(ml_path)
            if self.ml_predictor.model_loaded:
                logger.info(f"   ✅ ML model loaded from {ml_path}")
            else:
                logger.warning(f"   ⚠️ ML model not found - using fallback logic")
            
            # Step 5: Initialize position manager
            logger.info("Step 5/8: Initializing position manager...")
            self.position_manager = PositionManager()
            logger.info("   ✅ Position manager ready")
            
            # Step 6: Initialize MT5
            logger.info("Step 6/8: Connecting to MetaTrader 5...")
            self.initialize_mt5()
            logger.info("   ✅ MT5 connected")
            
            # Step 7: Setup health monitoring
            logger.info("Step 7/8: Setting up health monitoring...")
            self.setup_health_monitor()
            logger.info("   ✅ Health monitor ready")
            
            # Initialize trading state
            self.running = True
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_trade_check = datetime.now()
            self.daily_report_sent = False
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            logger.info("-" * 50)
            logger.info("✅ BOT INITIALIZATION COMPLETE")
            logger.info(f"   🔐 License: {self.license_client.license_tier}")
            logger.info(f"   🎯 Multi-TP Strategy: {self.config.get('tp_splits')}")
            logger.info(f"   📈 Min ML Confidence: {self.config.min_ml_confidence}")
            logger.info(f"   ⚠️ Max Daily Loss: {self.config.max_daily_loss}%")
            logger.info("-" * 50)
            
        except Exception as e:
            logger.critical(f"❌ FATAL: Bot initialization failed: {e}")
            logger.critical(f"   Traceback:\n{traceback.format_exc()}")
            raise
    
    def setup_health_monitor(self):
        """Setup MT5 connection health monitoring"""
        try:
            login = self.config.get('mt5_login')
            password = self.config.get('mt5_password')
            server = self.config.get('mt5_server')
            
            if not all([login, password, server]):
                login = os.getenv('MT5_LOGIN')
                password = os.getenv('MT5_PASSWORD')
                server = os.getenv('MT5_SERVER')
            
            self.health_monitor = create_health_monitor(
                login=int(login) if login else 0,
                password=password or '',
                server=server or '',
                telegram_token=self.config.telegram_token,
                telegram_chat_id=self.config.telegram_chat_id,
                check_interval=30
            )
            
            # Start health monitoring
            self.health_monitor.start()
            logger.info("🏥 Health monitor started (30s interval)")
            
        except Exception as e:
            logger.error(f"⚠️ Failed to setup health monitor: {e}")
            self.health_monitor = None
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        logger.info("🔌 Setting up signal handlers...")
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        logger.info("   ✅ SIGINT and SIGTERM handlers registered")
    
    def initialize_mt5(self):
        """Initialize MT5 connection with detailed logging"""
        logger.info("🔗 Initializing MT5 connection...")
        
        if not mt5.initialize():
            error = mt5.last_error()
            logger.critical(f"❌ MT5 initialization failed: {error}")
            raise Exception(f"MT5 initialization failed: {error}")
        
        logger.info("   ✅ MT5 terminal initialized")
        
        # Get terminal info
        terminal_info = mt5.terminal_info()
        if terminal_info:
            logger.info(f"   📊 Terminal: Build {terminal_info.build}")
            logger.info(f"   📊 Company: {terminal_info.company}")
            logger.info(f"   📊 Connected: {terminal_info.connected}")
        
        # Login if credentials provided
        login = os.getenv('MT5_LOGIN', self.config.get('mt5_login'))
        password = os.getenv('MT5_PASSWORD', self.config.get('mt5_password'))
        server = os.getenv('MT5_SERVER', self.config.get('mt5_server'))
        
        if login and password and server:
            logger.info(f"   🔑 Logging in to account {login}...")
            
            if not mt5.login(int(login), password, server):
                error = mt5.last_error()
                logger.critical(f"❌ MT5 login failed: {error}")
                raise Exception(f"MT5 login failed: {error}")
            
            logger.info("   ✅ Login successful")
        
        # Get account info
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"   👤 Account: {account_info.login}")
            logger.info(f"   💰 Balance: {account_info.balance} {account_info.currency}")
            logger.info(f"   💵 Equity: {account_info.equity} {account_info.currency}")
            logger.info(f"   📊 Leverage: 1:{account_info.leverage}")
        else:
            logger.warning("   ⚠️ Could not retrieve account info")
    
    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown with detailed logging"""
        logger.info("=" * 50)
        logger.info("🛑 SHUTDOWN INITIATED")
        logger.info("=" * 50)
        
        self.running = False
        
        # Stop health monitor
        if hasattr(self, 'health_monitor') and self.health_monitor:
            logger.info("🏥 Stopping health monitor...")
            self.health_monitor.stop()
            logger.info("   ✅ Health monitor stopped")
        
        # Send final report if needed
        if self.daily_trades > 0 and not self.daily_report_sent:
            logger.info("📊 Sending final daily report...")
            self.send_daily_report()
        
        # Shutdown MT5
        logger.info("🔗 Disconnecting from MT5...")
        mt5.shutdown()
        logger.info("   ✅ MT5 disconnected")
        
        # Save state
        logger.info("💾 Saving bot state...")
        self.state_manager.save_state({
            'last_shutdown': datetime.now().isoformat(),
            'status': 'stopped',
            'daily_trades': self.daily_trades,
            'daily_pnl': self.daily_pnl
        })
        logger.info("   ✅ State saved")
        
        logger.info("=" * 50)
        logger.info("✅ BOT STOPPED SAFELY")
        logger.info(f"📅 Shutdown Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        sys.exit(0)
    
    def get_account_balance(self) -> float:
        """Get current account balance"""
        account_info = mt5.account_info()
        if account_info:
            return account_info.balance
        logger.warning("⚠️ Could not retrieve account balance")
        return 0.0
    
    def calculate_position_size(self, symbol: str, stop_loss_pips: float) -> float:
        """Calculate position size based on risk"""
        logger.debug(f"📐 Calculating position size for {symbol}...")
        
        balance = self.get_account_balance()
        risk_amount = balance * (self.config.risk_per_trade / 100)
        
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.error(f"❌ Symbol info not found for {symbol}")
            return 0.0
        
        pip_value = 0.01 if "JPY" in symbol else 0.0001
        lot_size = risk_amount / (stop_loss_pips * pip_value * symbol_info.trade_contract_size)
        
        lot_step = symbol_info.volume_step
        lot_size = round(lot_size / lot_step) * lot_step
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
        
        logger.debug(f"   📐 Lot size: {lot_size} (risk: {risk_amount:.2f}, SL pips: {stop_loss_pips:.1f})")
        
        return lot_size
    
    def get_market_data(self, symbol: str, timeframe: str = "H1", bars: int = 200) -> Optional[pd.DataFrame]:
        """Fetch market data with logging"""
        logger.debug(f"📊 Fetching {bars} bars of {timeframe} data for {symbol}...")
        
        try:
            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe, mt5.TIMEFRAME_H1), 0, bars)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"⚠️ No data returned for {symbol}")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            logger.debug(f"   ✅ Got {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    def analyze_market(self, symbol: str) -> Optional[Dict]:
        """Analyze market conditions for a symbol"""
        logger.debug(f"🔍 Analyzing {symbol}...")
        
        try:
            df = self.get_market_data(symbol, "H1", 200)
            if df is None or len(df) < 100:
                logger.debug(f"   ⚠️ Insufficient data for {symbol}")
                return None
            
            indicators = calculate_indicators(df)
            if indicators is None:
                logger.warning(f"   ⚠️ Failed to calculate indicators for {symbol}")
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
            
            # Determine trend
            if current['ema_20'] > current['ema_50'] > current['ema_200']:
                trend = "Bull"
            elif current['ema_20'] < current['ema_50'] < current['ema_200']:
                trend = "Bear"
            else:
                trend = "Sideways"
            
            logger.debug(f"   📊 {symbol}: Trend={trend}, RSI={current['rsi']:.1f}, ADX={current['adx']:.1f}")
            
            # Prepare ML features
            ml_features = self.prepare_ml_features(df, indicators)
            ml_confidence, ml_signal = self.ml_predictor.predict(ml_features)
            
            logger.debug(f"   🤖 ML: Signal={ml_signal}, Confidence={ml_confidence:.2f}")
            
            # Generate signal
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
                logger.info(f"   🎯 SIGNAL: {symbol} {signal['direction']} (conf: {ml_confidence:.2f})")
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            logger.debug(traceback.format_exc())
            return None
    
    def prepare_ml_features(self, df: pd.DataFrame, indicators: pd.DataFrame) -> np.ndarray:
        """Prepare all 18 features for ML model"""
        try:
            latest = df.iloc[-1]
            latest_ind = indicators.iloc[-1]
            
            features = [
                latest_ind['rsi'],
                latest_ind['adx'],
                latest_ind['atr'],
                latest_ind['ema_20'],
                latest_ind['ema_50'],
                latest_ind['ema_200'],
                latest_ind['macd'],
                latest_ind['macd_signal'],
                latest_ind['macd_histogram'],
                latest_ind['bb_position'],
                latest_ind['trend_bull'],
                latest_ind['trend_bear'],
                latest_ind['price_change'],
                latest_ind['volatility'],
                datetime.now().hour,
                datetime.now().weekday(),
                latest['close'],
                latest['tick_volume']
            ]
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"❌ Error preparing ML features: {e}")
            return None
    
    def generate_signal(self, current: Dict, trend: str, ml_confidence: float, ml_signal: str) -> Optional[Dict]:
        """Generate trading signal based on analysis"""
        if ml_confidence < self.config.min_ml_confidence:
            logger.debug(f"   ⏭️ Skipping: ML confidence {ml_confidence:.2f} < {self.config.min_ml_confidence}")
            return None
        
        if current['adx'] < 20:
            logger.debug(f"   ⏭️ Skipping: ADX {current['adx']:.1f} < 20 (weak trend)")
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
        """Check if trading is allowed based on risk limits"""
        if self.daily_trades >= self.config.max_trades_per_day:
            logger.info(f"⚠️ Daily trade limit reached: {self.daily_trades}/{self.config.max_trades_per_day}")
            return False
        
        if self.daily_pnl <= -self.config.max_daily_loss:
            logger.warning(f"🛑 Daily loss limit reached: {self.daily_pnl:.2f}%")
            send_telegram_message(
                self.config.telegram_token,
                self.config.telegram_chat_id,
                f"🛑 TRADING STOPPED\n━━━━━━━━━━━━━━━━\nDaily loss limit reached: {self.daily_pnl:.2f}%\nBot will resume tomorrow."
            )
            return False
        
        open_positions = mt5.positions_total()
        if open_positions >= self.config.max_open_positions:
            logger.debug(f"⏸️ Max positions reached: {open_positions}/{self.config.max_open_positions}")
            return False
        
        return True
    
    def execute_multi_tp_trade(self, signal: Dict) -> bool:
        """Execute trade with 3 TP levels"""
        symbol = signal['symbol']
        direction = signal['direction']
        
        logger.info("=" * 50)
        logger.info(f"🚀 EXECUTING TRADE: {symbol} {direction}")
        logger.info("=" * 50)
        
        try:
            # Check symbol
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"❌ Symbol {symbol} not found")
                return False
            
            if not symbol_info.visible:
                logger.info(f"📊 Making {symbol} visible in Market Watch...")
                if not mt5.symbol_select(symbol, True):
                    logger.error(f"❌ Failed to select {symbol}")
                    return False
            
            # Calculate lot size
            pip_divisor = 0.01 if "JPY" in symbol else 0.0001
            stop_loss_pips = abs(signal['entry_price'] - signal['sl']) / pip_divisor
            total_lot = self.calculate_position_size(symbol, stop_loss_pips)
            
            logger.info(f"   📐 Total lot: {total_lot}")
            logger.info(f"   📐 SL pips: {stop_loss_pips:.1f}")
            
            if total_lot < symbol_info.volume_min:
                logger.warning(f"⚠️ Lot size {total_lot} too small (min: {symbol_info.volume_min})")
                return False
            
            # Split lots
            tp_splits = self.config.get('tp_splits', [0.40, 0.30, 0.30])
            lot_splits = [round(total_lot * split / symbol_info.volume_step) * symbol_info.volume_step 
                         for split in tp_splits]
            lot_splits[-1] = total_lot - sum(lot_splits[:-1])
            
            logger.info(f"   📊 Lot splits: {lot_splits}")
            
            # Get current price
            order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
            tick = mt5.symbol_info_tick(symbol)
            price = tick.ask if direction == "BUY" else tick.bid
            
            logger.info(f"   💵 Entry price: {price}")
            logger.info(f"   🛑 SL: {signal['sl']}")
            logger.info(f"   🎯 TP levels: {signal['tp_levels']}")
            
            # Execute orders
            orders_placed = []
            
            for i, (lot, tp) in enumerate(zip(lot_splits, signal['tp_levels'])):
                if lot < symbol_info.volume_min:
                    logger.warning(f"   ⚠️ TP{i+1} lot {lot} below minimum")
                    continue
                
                logger.info(f"   📤 Sending TP{i+1} order: {lot} lot @ TP={tp:.5f}")
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": order_type,
                    "price": price,
                    "sl": signal['sl'],
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
                    logger.info(f"   ✅ TP{i+1} placed: Ticket #{result.order}")
                else:
                    logger.error(f"   ❌ TP{i+1} failed: {result.retcode} - {result.comment}")
            
            if not orders_placed:
                logger.error("❌ No orders placed successfully")
                return False
            
            self.daily_trades += 1
            
            # Log trade
            log_trade(
                Symbol=symbol,
                Direction=direction,
                Lot=total_lot,
                EntryPrice=price,
                SL=signal['sl'],
                TP=signal['tp_levels'][2],
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
                    signal['sl'],
                    order['tp'],
                    order['tp_level']
                )
            
            # Telegram notification
            sl_pips = abs(price - signal['sl']) / pip_divisor
            tp_pips = [(abs(tp - price) / pip_divisor) for tp in signal['tp_levels']]
            
            msg = (
                f"🤖 TRADE OPENED\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"Symbol: {symbol}\n"
                f"Direction: {direction}\n"
                f"Total Lot: {total_lot}\n"
                f"Entry: {price}\n\n"
                f"🎯 Multiple Take Profits:\n"
                f"TP1 ({int(tp_splits[0]*100)}%): {signal['tp_levels'][0]:.5f} [+{tp_pips[0]:.1f} pips]\n"
                f"TP2 ({int(tp_splits[1]*100)}%): {signal['tp_levels'][1]:.5f} [+{tp_pips[1]:.1f} pips]\n"
                f"TP3 ({int(tp_splits[2]*100)}%): {signal['tp_levels'][2]:.5f} [+{tp_pips[2]:.1f} pips]\n"
                f"SL: {signal['sl']:.5f} [-{sl_pips:.1f} pips]\n\n"
                f"ML Confidence: {signal['ml_confidence']:.2f}"
            )
            
            send_telegram_message(
                self.config.telegram_token,
                self.config.telegram_chat_id,
                msg
            )
            
            logger.info("=" * 50)
            logger.info(f"✅ TRADE EXECUTED: {symbol} {direction}")
            logger.info(f"   Orders: {len(orders_placed)}")
            logger.info(f"   Daily trades: {self.daily_trades}")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error executing trade: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def monitor_positions(self):
        """Monitor and detect closed positions"""
        try:
            closed = self.position_manager.check_closed_positions()
            
            for pos in closed:
                logger.info(f"📊 Position closed: {pos['symbol']} TP{pos['tp_level']} - {pos['result']}")
                
                update_trade_result(
                    pos['symbol'],
                    pos['close_time'],
                    pos['result'],
                    pos['pnl_percent']
                )
                
                self.daily_pnl += pos['pnl_percent']
                
                # Notification
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
                
                logger.info(f"   {pos['symbol']} - {pos['result']} - {pos['pnl_percent']:+.2f}%")
                
        except Exception as e:
            logger.error(f"❌ Error monitoring positions: {e}")
    
    def reset_daily_counters(self):
        """Reset counters at start of new day"""
        now = datetime.now()
        if now.date() > self.last_trade_check.date():
            logger.info("=" * 50)
            logger.info("🌅 NEW TRADING DAY")
            logger.info("=" * 50)
            logger.info(f"   Previous day trades: {self.daily_trades}")
            logger.info(f"   Previous day PnL: {self.daily_pnl:.2f}%")
            
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.daily_report_sent = False
            self.last_trade_check = now
            self.position_manager.reset_daily_tracking()
            
            logger.info("   ✅ Counters reset")
    
    def scan_and_trade(self):
        """Scan markets and execute trades"""
        try:
            if not self.check_risk_limits():
                return
            
            trading_pairs = self.config.get('trading_pairs', [])
            logger.debug(f"🔍 Scanning {len(trading_pairs)} pairs...")
            
            for symbol in trading_pairs:
                if not self.check_risk_limits():
                    break
                
                if self.position_manager.has_open_positions(symbol):
                    logger.debug(f"   ⏭️ {symbol}: Already has open positions")
                    continue
                
                signal = self.analyze_market(symbol)
                if signal:
                    logger.info(f"🎯 SIGNAL DETECTED: {symbol} {signal['direction']}")
                    self.execute_multi_tp_trade(signal)
                    time.sleep(2)
                    
        except Exception as e:
            logger.error(f"❌ Error in scan_and_trade: {e}")
            logger.error(traceback.format_exc())
    
    def send_daily_report(self):
        """Generate and send daily report"""
        logger.info("📊 Generating daily report...")
        
        try:
            daily = DailyReport()
            pdf_file, stats = daily.generate()
            
            if pdf_file and stats:
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
                logger.info("   ✅ Daily report sent")
            else:
                logger.info("   ℹ️ No trades to report today")
                
        except Exception as e:
            logger.error(f"❌ Error sending report: {e}")
    
    def check_report_time(self):
        """Check if it's time to send daily report"""
        now = datetime.now()
        if now.hour >= 17 and self.daily_trades > 0 and not self.daily_report_sent:
            self.send_daily_report()
    
    def log_health_status(self):
        """Log current bot and connection health"""
        if self.health_monitor:
            status = self.health_monitor.get_status()
            logger.debug(f"🏥 Health: {status['status']}, Checks: {status['metrics']['checks_performed']}")
    
    def run(self):
        """Main bot loop"""
        logger.info("=" * 70)
        logger.info("🚀 BOT MAIN LOOP STARTING")
        logger.info("=" * 70)
        logger.info(f"   📊 Pairs: {self.config.get('trading_pairs')}")
        logger.info(f"   💰 Risk: {self.config.risk_per_trade}% per trade")
        logger.info(f"   🎯 Multi-TP: {self.config.get('tp_splits')}")
        logger.info(f"   ⏱️ Loop interval: {self.config.loop_interval}s")
        
        # Send startup notification
        send_telegram_message(
            self.config.telegram_token,
            self.config.telegram_chat_id,
            "🤖 Enhanced MT5 Bot Started!\n✅ Multi-TP Strategy Active\n✅ Health Monitoring Active\n✅ Ready to trade"
        )
        
        loop_count = 0
        
        while self.running:
            try:
                loop_count += 1
                logger.debug(f"--- Loop #{loop_count} ---")
                
                self.reset_daily_counters()
                self.monitor_positions()
                self.scan_and_trade()
                self.check_report_time()
                self.log_health_status()
                
                time.sleep(self.config.loop_interval)
                
            except KeyboardInterrupt:
                logger.info("⌨️ Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(30)
        
        self.shutdown()


def run_trading_bot():
    """Run the trading bot - called from main.py after setup wizard"""
    try:
        bot = MT5TradingBot()
        bot.run()
    except Exception as e:
        logger.critical(f"💀 FATAL ERROR: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)


def main():
    """Main entry point when run directly"""
    run_trading_bot()


if __name__ == "__main__":
    main()
