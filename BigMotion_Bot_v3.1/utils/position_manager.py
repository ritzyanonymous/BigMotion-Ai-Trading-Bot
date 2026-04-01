"""
Position Manager - Tracks Multi-TP positions
"""
import MetaTrader5 as mt5
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages and tracks multi-TP positions"""
    
    def __init__(self):
        self.tracked_positions = {}  # ticket: position_info
        self.closed_today = []
        self.symbol_pnl = {}  # symbol: total_pnl
    
    def add_position(self, ticket: int, symbol: str, direction: str, lot: float,
                    entry: float, sl: float, tp: float, tp_level: int):
        """Track a new position"""
        self.tracked_positions[ticket] = {
            'symbol': symbol,
            'direction': direction,
            'lot': lot,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'tp_level': tp_level,
            'open_time': datetime.now(),
            'status': 'OPEN'
        }
        logger.info(f"📍 Tracking position: {symbol} TP{tp_level} - Ticket {ticket}")
    
    def check_closed_positions(self) -> List[Dict]:
        """Check for closed positions and return list"""
        closed_list = []
        
        try:
            # Get all currently open positions from MT5
            open_positions = mt5.positions_get()
            open_tickets = {p.ticket for p in open_positions} if open_positions else set()
            
            # Check tracked positions
            for ticket, pos_info in list(self.tracked_positions.items()):
                if ticket not in open_tickets and pos_info['status'] == 'OPEN':
                    # Position was closed
                    pos_info['status'] = 'CLOSED'
                    pos_info['close_time'] = datetime.now()
                    
                    # Get close info from history
                    deals = mt5.history_deals_get(ticket=ticket)
                    
                    if deals and len(deals) > 0:
                        close_deal = deals[-1]
                        close_price = close_deal.price
                        profit = close_deal.profit
                        
                        # Calculate if TP or SL was hit
                        if pos_info['direction'] == 'BUY':
                            hit_tp = close_price >= pos_info['tp'] - 0.0001
                        else:
                            hit_tp = close_price <= pos_info['tp'] + 0.0001
                        
                        result = 'TP' if hit_tp else 'SL'
                        
                        # Calculate PnL percentage (approximate)
                        account_info = mt5.account_info()
                        balance = account_info.balance if account_info else 10000
                        pnl_percent = (profit / balance) * 100
                        
                        # Add to symbol PnL tracking
                        symbol = pos_info['symbol']
                        if symbol not in self.symbol_pnl:
                            self.symbol_pnl[symbol] = 0.0
                        self.symbol_pnl[symbol] += pnl_percent
                        
                        closed_info = {
                            'ticket': ticket,
                            'symbol': pos_info['symbol'],
                            'direction': pos_info['direction'],
                            'lot': pos_info['lot'],
                            'entry': pos_info['entry'],
                            'close_price': close_price,
                            'tp_level': pos_info['tp_level'],
                            'result': result,
                            'profit': profit,
                            'pnl_percent': pnl_percent,
                            'close_time': pos_info['close_time']
                        }
                        
                        closed_list.append(closed_info)
                        self.closed_today.append(closed_info)
                        
                        logger.info(f"✅ Detected closed: {pos_info['symbol']} TP{pos_info['tp_level']} - {result}")
        
        except Exception as e:
            logger.error(f"Error checking closed positions: {e}")
        
        return closed_list
    
    def has_open_positions(self, symbol: str) -> bool:
        """Check if symbol has any open positions"""
        for pos_info in self.tracked_positions.values():
            if pos_info['symbol'] == symbol and pos_info['status'] == 'OPEN':
                return True
        return False
    
    def get_open_positions_for_symbol(self, symbol: str) -> List[Dict]:
        """Get all open positions for a symbol"""
        return [
            pos_info for pos_info in self.tracked_positions.values()
            if pos_info['symbol'] == symbol and pos_info['status'] == 'OPEN'
        ]
    
    def get_total_pnl_for_symbol(self, symbol: str) -> float:
        """Get total PnL for a symbol (all TPs combined)"""
        return self.symbol_pnl.get(symbol, 0.0)
    
    def reset_daily_tracking(self):
        """Reset tracking for new day"""
        # Keep tracked positions but reset daily stats
        self.closed_today = []
        self.symbol_pnl = {}
        logger.info("📊 Position tracking reset for new day")
    
    def get_statistics(self) -> Dict:
        """Get current statistics"""
        total_open = sum(1 for p in self.tracked_positions.values() if p['status'] == 'OPEN')
        total_closed_today = len(self.closed_today)
        
        return {
            'open_positions': total_open,
            'closed_today': total_closed_today,
            'tracked_total': len(self.tracked_positions)
        }
