"""Configuration management - v3 compatible with v2 trading engine"""
import os
import json
from pathlib import Path
from typing import Dict, Any


class Config:
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.config = self.load_config()
        # NO strict validation - Telegram is optional
    
    def load_config(self) -> Dict[str, Any]:
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        else:
            config = self.create_default_config()
            self.save_config(config)
        
        # Support both bot_token and telegram_token
        if 'bot_token' in config.get('telegram', {}):
            config['telegram_token'] = config['telegram']['bot_token']
        elif 'telegram_token' in config.get('telegram', {}):
            config['telegram_token'] = config['telegram']['telegram_token']
        else:
            config['telegram_token'] = ""
        
        # Get telegram chat_id
        if 'chat_id' in config.get('telegram', {}):
            config['telegram_chat_id'] = config['telegram']['chat_id']
        else:
            config['telegram_chat_id'] = ""
        
        # Get MT5 credentials
        if 'mt5' in config:
            config['mt5_login'] = config['mt5'].get('login', '')
            config['mt5_password'] = config['mt5'].get('password', '')
            config['mt5_server'] = config['mt5'].get('server', '')
        
        # Get trading settings
        if 'trading' in config:
            config['risk_per_trade'] = config['trading'].get('risk_per_trade', 0.9)
            config['max_trades_per_day'] = config['trading'].get('max_trades_per_day', 3)
            config['max_daily_loss'] = config['trading'].get('max_daily_loss_percent', 5.0)
            config['tp_splits'] = config['trading'].get('tp_splits', [0.4, 0.3, 0.3])
        
        # Get symbols
        if 'symbols' in config:
            config['trading_pairs'] = config['symbols']
        
        # Get advanced settings
        if 'advanced' in config:
            config['loop_interval'] = config['advanced'].get('check_interval_seconds', 60)
            config['timeframe'] = config['advanced'].get('timeframe', 'H1')
        
        # ML model
        if 'ml_model' in config:
            config['ml_model_path'] = config['ml_model'].get('model_path', 'models/trading_model.pkl')
        
        # Environment variables override (optional)
        config['telegram_token'] = os.getenv('TELEGRAM_BOT_TOKEN', config.get('telegram_token', ''))
        config['telegram_chat_id'] = os.getenv('TELEGRAM_CHAT_ID', config.get('telegram_chat_id', ''))
        config['mt5_login'] = os.getenv('MT5_LOGIN', config.get('mt5_login', ''))
        config['mt5_password'] = os.getenv('MT5_PASSWORD', config.get('mt5_password', ''))
        config['mt5_server'] = os.getenv('MT5_SERVER', config.get('mt5_server', ''))
        
        return config
    
    def create_default_config(self) -> Dict[str, Any]:
        return {
            "telegram_token": "",
            "telegram_chat_id": "",
            "mt5_login": "",
            "mt5_password": "",
            "mt5_server": "",
            "loop_interval": 60,
            "trading_pairs": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "USDCHF", "USDCNH", "AUDUSD", "NZDUSD"],
            "timeframe": "H1",
            "risk_per_trade": 0.9,
            "max_trades_per_day": 3,
            "max_daily_loss": 5.0,
            "max_open_positions": 5,
            "min_ml_confidence": 0.65,
            "tp_splits": [0.40, 0.30, 0.30],
            "ml_model_path": "models/trading_model.pkl"
        }
    
    def save_config(self, config: Dict[str, Any]):
        safe_config = config.copy()
        for key in ['telegram_token', 'telegram_chat_id', 'mt5_login', 'mt5_password', 'mt5_server']:
            if key in safe_config:
                safe_config[key] = ""
        with open(self.config_path, 'w') as f:
            json.dump(safe_config, f, indent=4)
    
    # Properties for v2 compatibility (accessed as config.risk_per_trade)
    @property
    def telegram_token(self) -> str:
        return self.config.get('telegram_token', '')
    
    @property
    def telegram_chat_id(self) -> str:
        return self.config.get('telegram_chat_id', '')
    
    @property
    def loop_interval(self) -> int:
        return self.config.get('loop_interval', 60)
    
    @property
    def risk_per_trade(self) -> float:
        return self.config.get('risk_per_trade', 0.9)
    
    @property
    def max_trades_per_day(self) -> int:
        return self.config.get('max_trades_per_day', 3)
    
    @property
    def max_daily_loss(self) -> float:
        return self.config.get('max_daily_loss', 5.0)
    
    @property
    def max_open_positions(self) -> int:
        return self.config.get('max_open_positions', 5)
    
    @property
    def min_ml_confidence(self) -> float:
        return self.config.get('min_ml_confidence', 0.65)
    
    @property
    def trading_pairs(self) -> list:
        return self.config.get('trading_pairs', ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"])
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
