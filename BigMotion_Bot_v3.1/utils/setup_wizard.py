"""
BigMotion Trading Bot - Interactive Setup Wizard
Prompts users for configuration instead of manual JSON editing

IMPORTANT: Set your Telegram Bot Token below!
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional
import getpass

# ============================================================
# CONFIGURATION: SET YOUR TELEGRAM BOT TOKEN HERE
# ============================================================
# 
# To create a bot:
# 1. Open Telegram and search for @BotFather
# 2. Send /newbot and follow instructions
# 3. BotFather will give you a token
# 4. Paste it below (replace 'YOUR_BOT_TOKEN_HERE')
#
# Example: '123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890'
#
TELEGRAM_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'  # ← PUT YOUR BOT TOKEN HERE!
#
# Once you set this token and rebuild the .exe:
# - All customers will get notifications from YOUR bot
# - They only need to provide their Chat ID
# - Simple and professional!
# ============================================================

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

class SetupWizard:
    """Interactive setup wizard for first-time configuration"""
    
    def __init__(self):
        self.config_path = Path("config.json")
        self.config = {}
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60 + "\n")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"✅ {message}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"❌ {message}")
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"ℹ️  {message}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"⚠️  {message}")
    
    def get_input(self, prompt: str, default: str = None, required: bool = True) -> str:
        """Get user input with validation"""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if user_input or not required:
                return user_input
            
            self.print_error("This field is required. Please enter a value.")
    
    def get_password(self, prompt: str) -> str:
        """Get password input (hidden)"""
        while True:
            password = getpass.getpass(f"{prompt}: ")
            if password:
                return password
            self.print_error("Password cannot be empty.")
    
    def get_number(self, prompt: str, default: float = None) -> float:
        """Get numeric input"""
        while True:
            if default is not None:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            try:
                return float(user_input)
            except ValueError:
                self.print_error("Please enter a valid number.")
    
    def get_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no input"""
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            
            if not response:
                return default
            
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            
            self.print_error("Please enter 'y' or 'n'.")
    
    def welcome(self):
        """Show welcome message"""
        self.clear_screen()
        self.print_header("🤖 BIGMOTION AUTOFX - FIRST TIME SETUP")
        
        print("""
Welcome to BigMotion AutoFX Trading Bot! 🎉

This setup wizard will help you configure the bot in just a few steps.

You'll need:
  1. Your Telegram Chat ID (from @userinfobot)
  2. MT5 broker login credentials
  3. Basic trading preferences

The setup takes about 2 minutes. Let's get started!
""")
        
        input("Press Enter to continue...")
    
    def setup_telegram(self):
        """Setup Telegram configuration"""
        self.clear_screen()
        self.print_header("📱 TELEGRAM CONFIGURATION")
        
        print("""
To receive trading alerts on Telegram:

1. Open Telegram and search for: @userinfobot
2. Send /start to the bot
3. It will reply with your Chat ID (a number like: 123456789)
4. Copy that number and paste it below

""")
        
        chat_id = self.get_input("Enter your Telegram Chat ID")
        
        # Validate it's a number
        try:
            int(chat_id)
        except ValueError:
            self.print_error("Invalid Chat ID. Please enter numbers only.")
            return self.setup_telegram()
        
        # Use the configured bot token
        bot_token = TELEGRAM_BOT_TOKEN
        
        # Check if token is still placeholder
        if bot_token == 'YOUR_BOT_TOKEN_HERE':
            self.print_warning("Telegram bot token not configured!")
            self.print_info("You'll need to set TELEGRAM_BOT_TOKEN in setup_wizard.py")
            self.print_info("For now, Telegram alerts will be disabled.")
            send_alerts = False
        else:
            send_alerts = True
            self.print_success("Telegram bot configured - you'll receive trade alerts!")
        
        self.config['telegram'] = {
            'chat_id': chat_id,
            'bot_token': bot_token,
            'send_alerts': send_alerts
        }
        
        self.print_success(f"Telegram Chat ID saved: {chat_id}")
        input("\nPress Enter to continue...")
    
    def setup_mt5(self):
        """Setup MT5 broker configuration"""
        self.clear_screen()
        self.print_header("🏦 MT5 BROKER CONFIGURATION")
        
        print("""
Enter your MetaTrader 5 broker credentials:

Make sure you have:
  • Your MT5 account login (account number)
  • Your MT5 password
  • Your broker's server name

""")
        
        login = self.get_input("MT5 Account Login (account number)")
        
        # Validate login is numeric
        try:
            int(login)
        except ValueError:
            self.print_error("Invalid login. Please enter your account number (numbers only).")
            return self.setup_mt5()
        
        password = self.get_password("MT5 Password (input hidden)")
        
        print("\nCommon MT5 servers:")
        print("  • IC Markets: ICMarkets-Demo / ICMarkets-Live")
        print("  • XM: XM.com-Demo / XM.com-Real")
        print("  • FTMO: FTMO-Server / FTMO-Server2")
        print("  • Vantage: VantageInternational-Demo / VantageInternational-Live")
        print("  • Your broker's server name (check MT5 terminal)\n")
        
        server = self.get_input("MT5 Server Name")
        
        self.config['mt5'] = {
            'login': login,
            'password': password,
            'server': server,
            'timeout': 60000,
            'path': ''  # Auto-detect MT5 terminal
        }
        
        self.print_success("MT5 credentials saved")
        
        # Test connection
        if self.get_yes_no("\nTest MT5 connection now?", True):
            self.test_mt5_connection()
        
        input("\nPress Enter to continue...")
    
    def test_mt5_connection(self):
        """Test MT5 connection"""
        if not mt5:
            self.print_error("MetaTrader5 package not available. Skipping test.")
            return
        
        print("\n🔄 Testing MT5 connection...")
        
        try:
            if not mt5.initialize():
                self.print_error(f"MT5 initialization failed: {mt5.last_error()}")
                return
            
            login_result = mt5.login(
                int(self.config['mt5']['login']),
                self.config['mt5']['password'],
                self.config['mt5']['server']
            )
            
            if login_result:
                account_info = mt5.account_info()
                self.print_success("MT5 connection successful!")
                print(f"   Account: {account_info.login}")
                print(f"   Balance: ${account_info.balance:,.2f}")
                print(f"   Broker: {account_info.company}")
            else:
                error = mt5.last_error()
                self.print_error(f"MT5 login failed: {error}")
                
                if self.get_yes_no("Re-enter MT5 credentials?", True):
                    return self.setup_mt5()
            
            mt5.shutdown()
            
        except Exception as e:
            self.print_error(f"Connection test failed: {e}")
            if self.get_yes_no("Re-enter MT5 credentials?", True):
                return self.setup_mt5()
    
    def setup_trading_preferences(self):
        """Setup trading preferences"""
        self.clear_screen()
        self.print_header("⚙️ TRADING PREFERENCES")
        
        print("""
Configure your trading risk parameters:

These settings control how the bot manages risk.
Default values are conservative and recommended for beginners.

""")
        
        risk_per_trade = self.get_number("Risk per trade (%)", 0.9)
        max_trades_per_day = int(self.get_number("Maximum trades per day", 3))
        max_daily_loss = self.get_number("Maximum daily loss (%)", 5.0)
        
        self.config['trading'] = {
            'risk_per_trade': risk_per_trade,
            'max_trades_per_day': max_trades_per_day,
            'max_daily_loss_percent': max_daily_loss,
            'use_multi_tp': True,
            'tp_splits': [0.4, 0.3, 0.3]
        }
        
        self.config['symbols'] = [
            "EURUSD", "GBPUSD", "USDJPY", "XAUUSD",
            "USDCHF", "USDCNH", "AUDUSD", "NZDUSD"
        ]
        
        self.print_success("Trading preferences saved")
        input("\nPress Enter to continue...")
    
    def setup_advanced(self):
        """Setup advanced options (optional)"""
        self.clear_screen()
        self.print_header("🔧 ADVANCED OPTIONS (Optional)")
        
        print("""
These are optional advanced settings.
Press Enter to use defaults, or customize if needed.

""")
        
        if self.get_yes_no("Configure advanced options?", False):
            
            timeframe = self.get_input("Trading timeframe", "H1")
            magic_number = int(self.get_number("Magic number (unique ID)", 20260124))
            
            self.config['advanced'] = {
                'timeframe': timeframe,
                'magic_number': magic_number,
                'slippage': 3,
                'check_interval_seconds': 60
            }
            
            self.print_success("Advanced options saved")
        else:
            self.config['advanced'] = {
                'timeframe': 'H1',
                'magic_number': 20260124,
                'slippage': 3,
                'check_interval_seconds': 60
            }
            self.print_info("Using default advanced options")
        
        input("\nPress Enter to continue...")
    
    def save_config(self):
        """Save configuration to file"""
        self.clear_screen()
        self.print_header("💾 SAVING CONFIGURATION")
        
        try:
            # Create complete config
            complete_config = {
                'mt5': self.config.get('mt5', {}),
                'telegram': self.config.get('telegram', {}),
                'trading': self.config.get('trading', {}),
                'symbols': self.config.get('symbols', []),
                'advanced': self.config.get('advanced', {}),
                'ml_model': {
                    'use_ml': True,
                    'model_path': 'models/trading_model.pkl',
                    'retrain_interval_days': 7
                }
            }
            
            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(complete_config, f, indent=4)
            
            self.print_success(f"Configuration saved to: {self.config_path}")
            
        except Exception as e:
            self.print_error(f"Failed to save configuration: {e}")
            sys.exit(1)
    
    def summary(self):
        """Show configuration summary"""
        self.clear_screen()
        self.print_header("📋 CONFIGURATION SUMMARY")
        
        telegram_status = "✅ Enabled" if self.config['telegram'].get('send_alerts', False) else "⚠️  Disabled (no bot token)"
        
        print(f"""
✅ Setup Complete!

Your configuration:

📱 Telegram:
   Chat ID: {self.config['telegram']['chat_id']}
   Alerts: {telegram_status}

🏦 MT5 Broker:
   Account: {self.config['mt5']['login']}
   Server: {self.config['mt5']['server']}

⚙️ Trading:
   Risk per trade: {self.config['trading']['risk_per_trade']}%
   Max trades/day: {self.config['trading']['max_trades_per_day']}
   Max daily loss: {self.config['trading']['max_daily_loss_percent']}%

💱 Trading Pairs:
   {', '.join(self.config['symbols'][:4])}... ({len(self.config['symbols'])} total)

Configuration saved to: {self.config_path}

""")
        
        if not self.config['telegram'].get('send_alerts', False):
            print("=" * 60)
            self.print_warning("Telegram alerts are DISABLED")
            print("To enable: Set TELEGRAM_BOT_TOKEN in setup_wizard.py")
            print("=" * 60)
            print()
        
        print("=" * 60)
        print("🚀 The bot is now ready to start trading!")
        print("=" * 60)
        
        input("\nPress Enter to start the bot...")
    
    def run(self) -> bool:
        """Run the setup wizard"""
        try:
            self.welcome()
            self.setup_telegram()
            self.setup_mt5()
            self.setup_trading_preferences()
            self.setup_advanced()
            self.save_config()
            self.summary()
            return True
            
        except KeyboardInterrupt:
            print("\n\n❌ Setup cancelled by user.")
            return False
        except Exception as e:
            print(f"\n\n❌ Setup failed: {e}")
            return False


def needs_setup() -> bool:
    """Check if setup is needed"""
    config_path = Path("config.json")
    
    # No config file
    if not config_path.exists():
        return True
    
    # Check if config is valid
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Check required fields
        required_fields = [
            ('mt5', 'login'),
            ('mt5', 'password'),
            ('mt5', 'server'),
            ('telegram', 'chat_id')
        ]
        
        for field_path in required_fields:
            section, key = field_path
            if section not in config:
                return True
            if key not in config[section]:
                return True
            # Check if it's still placeholder
            if config[section][key] in ['', 'YOUR_', None]:
                return True
        
        return False
        
    except Exception:
        return True


def run_setup_wizard() -> bool:
    """Run setup wizard if needed"""
    if needs_setup():
        wizard = SetupWizard()
        return wizard.run()
    return True


if __name__ == '__main__':
    # Test the wizard
    wizard = SetupWizard()
    wizard.run()
