"""
Watchdog - Auto-Restart Wrapper for Trading Bot
Monitors the main bot process and restarts it on failure
"""
import os
import sys
import time
import signal
import subprocess
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WATCHDOG - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('watchdog.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class BotWatchdog:
    """
    Watchdog that monitors and auto-restarts the trading bot
    """
    
    def __init__(
        self,
        bot_script: str = 'main.py',
        max_restarts: int = 10,
        restart_cooldown: int = 60,
        restart_window: int = 3600,
        health_check_interval: int = 60,
        telegram_token: str = None,
        telegram_chat_id: str = None
    ):
        """
        Initialize watchdog
        
        Args:
            bot_script: Path to the main bot script
            max_restarts: Maximum restarts allowed within restart_window
            restart_cooldown: Seconds to wait before restarting after crash
            restart_window: Time window (seconds) for counting restarts
            health_check_interval: Seconds between process health checks
            telegram_token: Optional Telegram bot token for notifications
            telegram_chat_id: Optional Telegram chat ID for notifications
        """
        self.bot_script = bot_script
        self.max_restarts = max_restarts
        self.restart_cooldown = restart_cooldown
        self.restart_window = restart_window
        self.health_check_interval = health_check_interval
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        
        self.process: Optional[subprocess.Popen] = None
        self.running = True
        self.restart_times = []
        self.total_restarts = 0
        self.start_time = None
        self.last_crash_reason = None
        
        # State file for persistence
        self.state_file = 'watchdog_state.json'
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        logger.info("=" * 60)
        logger.info("🐕 WATCHDOG INITIALIZED")
        logger.info(f"   Bot script: {self.bot_script}")
        logger.info(f"   Max restarts: {self.max_restarts} per {self.restart_window}s")
        logger.info(f"   Restart cooldown: {self.restart_cooldown}s")
        logger.info("=" * 60)
    
    def send_notification(self, message: str):
        """Send Telegram notification"""
        if not self.telegram_token or not self.telegram_chat_id:
            return
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            response = requests.post(
                url,
                data={'chat_id': self.telegram_chat_id, 'text': message},
                timeout=10
            )
            if response.status_code != 200:
                logger.warning(f"Telegram notification failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Telegram error: {e}")
    
    def check_restart_limit(self) -> bool:
        """
        Check if we've exceeded restart limits
        
        Returns:
            True if restart is allowed, False if limit exceeded
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.restart_window)
        
        # Filter restart times within the window
        self.restart_times = [t for t in self.restart_times if t > window_start]
        
        if len(self.restart_times) >= self.max_restarts:
            logger.error(f"❌ Restart limit exceeded: {len(self.restart_times)}/{self.max_restarts} in {self.restart_window}s")
            return False
        
        return True
    
    def start_bot(self) -> bool:
        """
        Start the bot process
        
        Returns:
            True if started successfully, False otherwise
        """
        if not Path(self.bot_script).exists():
            logger.error(f"❌ Bot script not found: {self.bot_script}")
            return False
        
        try:
            logger.info(f"🚀 Starting bot: {self.bot_script}")
            
            # Start the bot process
            self.process = subprocess.Popen(
                [sys.executable, self.bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            self.start_time = datetime.now()
            
            logger.info(f"✅ Bot started with PID: {self.process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            self.last_crash_reason = str(e)
            return False
    
    def stop_bot(self):
        """Stop the bot process gracefully"""
        if self.process and self.process.poll() is None:
            logger.info("🛑 Stopping bot process...")
            
            try:
                # Try graceful shutdown first
                self.process.terminate()
                
                try:
                    self.process.wait(timeout=10)
                    logger.info("✅ Bot stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("⚠️ Bot didn't stop gracefully, force killing...")
                    self.process.kill()
                    self.process.wait()
                    logger.info("✅ Bot force killed")
                    
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")
    
    def check_process_health(self) -> bool:
        """
        Check if bot process is still running
        
        Returns:
            True if running, False if crashed/stopped
        """
        if self.process is None:
            return False
        
        return_code = self.process.poll()
        
        if return_code is not None:
            # Process has terminated
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            if return_code == 0:
                logger.info(f"ℹ️ Bot exited normally (code 0) after {uptime:.0f}s")
                self.last_crash_reason = "Normal exit"
            else:
                logger.error(f"❌ Bot crashed (code {return_code}) after {uptime:.0f}s")
                self.last_crash_reason = f"Exit code: {return_code}"
                
                # Try to get last output for debugging
                try:
                    if self.process.stdout:
                        last_output = self.process.stdout.read()
                        if last_output:
                            logger.error(f"Last output: {last_output[-1000:]}")  # Last 1000 chars
                except:
                    pass
            
            return False
        
        return True
    
    def handle_crash(self):
        """Handle bot crash - decide whether to restart"""
        
        if not self.check_restart_limit():
            msg = (
                f"🛑 WATCHDOG STOPPED\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"Too many restarts ({self.max_restarts} in {self.restart_window}s)\n"
                f"Last crash: {self.last_crash_reason}\n"
                f"Manual intervention required!"
            )
            logger.critical(msg)
            self.send_notification(msg)
            self.running = False
            return
        
        self.restart_times.append(datetime.now())
        self.total_restarts += 1
        
        msg = (
            f"🔄 BOT RESTART #{self.total_restarts}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Reason: {self.last_crash_reason}\n"
            f"Restarting in {self.restart_cooldown}s..."
        )
        logger.warning(msg)
        self.send_notification(msg)
        
        # Wait before restart
        logger.info(f"⏳ Waiting {self.restart_cooldown}s before restart...")
        time.sleep(self.restart_cooldown)
        
        # Restart the bot
        if self.start_bot():
            msg = (
                f"✅ BOT RESTARTED\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"PID: {self.process.pid}\n"
                f"Total restarts: {self.total_restarts}"
            )
            logger.info(msg)
            self.send_notification(msg)
        else:
            logger.error("❌ Failed to restart bot")
    
    def save_state(self):
        """Save watchdog state to file"""
        state = {
            'total_restarts': self.total_restarts,
            'restart_times': [t.isoformat() for t in self.restart_times],
            'last_crash_reason': self.last_crash_reason,
            'last_update': datetime.now().isoformat()
        }
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def load_state(self):
        """Load watchdog state from file"""
        if not Path(self.state_file).exists():
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.total_restarts = state.get('total_restarts', 0)
            self.last_crash_reason = state.get('last_crash_reason')
            
            # Load restart times (filter old ones)
            window_start = datetime.now() - timedelta(seconds=self.restart_window)
            restart_times = state.get('restart_times', [])
            self.restart_times = [
                datetime.fromisoformat(t) for t in restart_times
                if datetime.fromisoformat(t) > window_start
            ]
            
            logger.info(f"📂 Loaded state: {self.total_restarts} total restarts")
            
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    
    def shutdown(self, signum=None, frame=None):
        """Shutdown watchdog and bot"""
        logger.info("🛑 Watchdog shutdown requested...")
        self.running = False
        self.stop_bot()
        self.save_state()
        logger.info("✅ Watchdog shutdown complete")
        sys.exit(0)
    
    def run(self):
        """Main watchdog loop"""
        logger.info("🐕 Watchdog starting...")
        
        # Load previous state
        self.load_state()
        
        # Start the bot
        if not self.start_bot():
            logger.critical("❌ Failed to start bot on initial attempt")
            self.send_notification(
                "❌ WATCHDOG FAILED\n━━━━━━━━━━━━━━━━\n"
                "Could not start bot on initial attempt.\n"
                f"Script: {self.bot_script}"
            )
            return
        
        self.send_notification(
            f"🐕 WATCHDOG STARTED\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Monitoring: {self.bot_script}\n"
            f"PID: {self.process.pid}\n"
            f"Auto-restart enabled"
        )
        
        # Main monitoring loop
        while self.running:
            try:
                # Read and log bot output (non-blocking)
                if self.process and self.process.stdout:
                    try:
                        # Use select for non-blocking read on Unix, or just read on Windows
                        import select
                        if hasattr(select, 'select'):
                            readable, _, _ = select.select([self.process.stdout], [], [], 0.1)
                            if readable:
                                line = self.process.stdout.readline()
                                if line:
                                    print(f"[BOT] {line.rstrip()}")
                    except:
                        pass
                
                # Check if bot is still running
                if not self.check_process_health():
                    self.handle_crash()
                
                # Save state periodically
                self.save_state()
                
                # Sleep between checks
                time.sleep(self.health_check_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                time.sleep(5)
        
        self.shutdown()


def get_config_values() -> tuple:
    """Get Telegram credentials from config if available"""
    try:
        config_path = 'config.json'
        if Path(config_path).exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            token = os.getenv('TELEGRAM_BOT_TOKEN', config.get('telegram_token', ''))
            chat_id = os.getenv('TELEGRAM_CHAT_ID', config.get('telegram_chat_id', ''))
            return token, chat_id
    except:
        pass
    
    return os.getenv('TELEGRAM_BOT_TOKEN', ''), os.getenv('TELEGRAM_CHAT_ID', '')


def main():
    parser = argparse.ArgumentParser(description='Trading Bot Watchdog - Auto-restart on failure')
    parser.add_argument('--script', default='main.py', help='Bot script to run (default: main.py)')
    parser.add_argument('--max-restarts', type=int, default=10, help='Max restarts per window (default: 10)')
    parser.add_argument('--cooldown', type=int, default=60, help='Seconds between restarts (default: 60)')
    parser.add_argument('--window', type=int, default=3600, help='Restart window in seconds (default: 3600)')
    parser.add_argument('--check-interval', type=int, default=30, help='Health check interval (default: 30)')
    
    args = parser.parse_args()
    
    # Get Telegram credentials
    telegram_token, telegram_chat_id = get_config_values()
    
    # Create and run watchdog
    watchdog = BotWatchdog(
        bot_script=args.script,
        max_restarts=args.max_restarts,
        restart_cooldown=args.cooldown,
        restart_window=args.window,
        health_check_interval=args.check_interval,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id
    )
    
    watchdog.run()


if __name__ == "__main__":
    main()
