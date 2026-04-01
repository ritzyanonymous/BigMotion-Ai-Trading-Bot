"""
MT5 Health Check Module
Monitors MT5 connection and auto-reconnects if needed
"""
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class MT5HealthCheck:
    """
    Monitors MT5 connection health and handles reconnection
    """
    
    def __init__(
        self,
        check_interval: int = 30,
        max_reconnect_attempts: int = 5,
        reconnect_delay: int = 10,
        on_disconnect: Optional[Callable] = None,
        on_reconnect: Optional[Callable] = None,
        on_failure: Optional[Callable] = None
    ):
        """
        Initialize health check monitor
        
        Args:
            check_interval: Seconds between health checks
            max_reconnect_attempts: Max reconnection attempts before giving up
            reconnect_delay: Seconds to wait between reconnection attempts
            on_disconnect: Callback when disconnection detected
            on_reconnect: Callback when successfully reconnected
            on_failure: Callback when all reconnection attempts fail
        """
        self.check_interval = check_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        self.on_disconnect = on_disconnect
        self.on_reconnect = on_reconnect
        self.on_failure = on_failure
        
        self.status = ConnectionStatus.DISCONNECTED
        self.last_check = None
        self.last_successful_check = None
        self.consecutive_failures = 0
        self.total_disconnections = 0
        self.total_reconnections = 0
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # MT5 credentials (set via set_credentials)
        self._login = None
        self._password = None
        self._server = None
        
        # Health metrics
        self.metrics = {
            'checks_performed': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'reconnections': 0,
            'total_downtime_seconds': 0,
            'last_downtime_start': None
        }
    
    def set_credentials(self, login: int, password: str, server: str):
        """Set MT5 login credentials for reconnection"""
        self._login = login
        self._password = password
        self._server = server
        logger.info("🔑 MT5 credentials configured for health check")
    
    def check_connection(self) -> bool:
        """
        Perform a single health check on MT5 connection
        
        Returns:
            True if connected and healthy, False otherwise
        """
        try:
            import MetaTrader5 as mt5
            
            self.last_check = datetime.now()
            self.metrics['checks_performed'] += 1
            
            # Check if MT5 is initialized
            terminal_info = mt5.terminal_info()
            
            if terminal_info is None:
                logger.warning("⚠️ MT5 terminal info unavailable")
                self.metrics['failed_checks'] += 1
                return False
            
            # Check connection status
            if not terminal_info.connected:
                logger.warning("⚠️ MT5 terminal not connected to broker")
                self.metrics['failed_checks'] += 1
                return False
            
            # Try to get account info as deeper health check
            account_info = mt5.account_info()
            if account_info is None:
                logger.warning("⚠️ Cannot retrieve MT5 account info")
                self.metrics['failed_checks'] += 1
                return False
            
            # Connection is healthy
            self.last_successful_check = datetime.now()
            self.metrics['successful_checks'] += 1
            
            # Reset failure counter on success
            if self.consecutive_failures > 0:
                logger.info(f"✅ MT5 connection restored after {self.consecutive_failures} failed checks")
                self.consecutive_failures = 0
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Health check exception: {e}")
            self.metrics['failed_checks'] += 1
            return False
    
    def reconnect(self) -> bool:
        """
        Attempt to reconnect to MT5
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if not all([self._login, self._password, self._server]):
            logger.error("❌ Cannot reconnect: MT5 credentials not set")
            return False
        
        try:
            import MetaTrader5 as mt5
            
            logger.info("🔄 Attempting MT5 reconnection...")
            
            # First, try to shutdown cleanly
            try:
                mt5.shutdown()
            except:
                pass
            
            time.sleep(2)
            
            # Re-initialize
            if not mt5.initialize():
                error = mt5.last_error()
                logger.error(f"❌ MT5 re-initialization failed: {error}")
                return False
            
            logger.info("✅ MT5 re-initialized")
            
            # Re-login
            if not mt5.login(int(self._login), self._password, self._server):
                error = mt5.last_error()
                logger.error(f"❌ MT5 re-login failed: {error}")
                return False
            
            # Verify connection
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"✅ MT5 reconnected - Account: {account_info.login}, Balance: {account_info.balance}")
                self.metrics['reconnections'] += 1
                self.total_reconnections += 1
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Reconnection exception: {e}")
            return False
    
    def handle_disconnection(self):
        """Handle detected disconnection with reconnection attempts"""
        with self._lock:
            if self.status == ConnectionStatus.RECONNECTING:
                return  # Already handling reconnection
            
            self.status = ConnectionStatus.RECONNECTING
            self.total_disconnections += 1
            self.metrics['last_downtime_start'] = datetime.now()
        
        logger.warning("🔴 MT5 DISCONNECTION DETECTED")
        
        # Call disconnect callback
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception as e:
                logger.error(f"Disconnect callback error: {e}")
        
        # Attempt reconnection
        for attempt in range(1, self.max_reconnect_attempts + 1):
            logger.info(f"🔄 Reconnection attempt {attempt}/{self.max_reconnect_attempts}")
            
            if self.reconnect():
                with self._lock:
                    self.status = ConnectionStatus.CONNECTED
                    self.consecutive_failures = 0
                    
                    # Calculate downtime
                    if self.metrics['last_downtime_start']:
                        downtime = (datetime.now() - self.metrics['last_downtime_start']).total_seconds()
                        self.metrics['total_downtime_seconds'] += downtime
                        self.metrics['last_downtime_start'] = None
                
                logger.info(f"✅ Reconnection successful on attempt {attempt}")
                
                # Call reconnect callback
                if self.on_reconnect:
                    try:
                        self.on_reconnect()
                    except Exception as e:
                        logger.error(f"Reconnect callback error: {e}")
                
                return
            
            if attempt < self.max_reconnect_attempts:
                logger.info(f"⏳ Waiting {self.reconnect_delay}s before next attempt...")
                time.sleep(self.reconnect_delay)
        
        # All attempts failed
        with self._lock:
            self.status = ConnectionStatus.FAILED
        
        logger.critical(f"❌ ALL {self.max_reconnect_attempts} RECONNECTION ATTEMPTS FAILED")
        
        # Call failure callback
        if self.on_failure:
            try:
                self.on_failure()
            except Exception as e:
                logger.error(f"Failure callback error: {e}")
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in separate thread)"""
        logger.info(f"🏥 Health monitor started (interval: {self.check_interval}s)")
        
        while self._running:
            try:
                is_healthy = self.check_connection()
                
                if is_healthy:
                    with self._lock:
                        if self.status != ConnectionStatus.CONNECTED:
                            self.status = ConnectionStatus.CONNECTED
                            logger.info("🟢 MT5 connection healthy")
                else:
                    self.consecutive_failures += 1
                    logger.warning(f"⚠️ Health check failed (consecutive: {self.consecutive_failures})")
                    
                    # Trigger reconnection after 2 consecutive failures
                    if self.consecutive_failures >= 2:
                        self.handle_disconnection()
                
            except Exception as e:
                logger.error(f"❌ Monitor loop error: {e}")
                self.consecutive_failures += 1
            
            # Sleep in small increments to allow faster shutdown
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)
        
        logger.info("🛑 Health monitor stopped")
    
    def start(self):
        """Start the health monitoring thread"""
        if self._running:
            logger.warning("Health monitor already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("🏥 Health monitor thread started")
    
    def stop(self):
        """Stop the health monitoring thread"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("🛑 Health monitor thread stopped")
    
    def get_status(self) -> Dict:
        """Get current health status and metrics"""
        with self._lock:
            return {
                'status': self.status.value,
                'last_check': self.last_check.isoformat() if self.last_check else None,
                'last_successful_check': self.last_successful_check.isoformat() if self.last_successful_check else None,
                'consecutive_failures': self.consecutive_failures,
                'total_disconnections': self.total_disconnections,
                'total_reconnections': self.total_reconnections,
                'metrics': self.metrics.copy()
            }
    
    def is_healthy(self) -> bool:
        """Quick check if connection is currently healthy"""
        with self._lock:
            return self.status == ConnectionStatus.CONNECTED


class HealthCheckCallbacks:
    """Pre-built callback handlers for common scenarios"""
    
    @staticmethod
    def telegram_notify(bot_token: str, chat_id: str):
        """Create Telegram notification callbacks"""
        
        def send_message(text: str):
            try:
                import requests
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                requests.post(url, data={'chat_id': chat_id, 'text': text}, timeout=10)
            except Exception as e:
                logger.error(f"Telegram notification error: {e}")
        
        def on_disconnect():
            send_message("🔴 MT5 DISCONNECTED\n━━━━━━━━━━━━━━━━\nAttempting to reconnect...")
        
        def on_reconnect():
            send_message("🟢 MT5 RECONNECTED\n━━━━━━━━━━━━━━━━\nTrading resumed")
        
        def on_failure():
            send_message("❌ MT5 CONNECTION FAILED\n━━━━━━━━━━━━━━━━\nAll reconnection attempts failed!\nManual intervention required.")
        
        return on_disconnect, on_reconnect, on_failure


# Convenience function to create and start health monitor
def create_health_monitor(
    login: int,
    password: str,
    server: str,
    telegram_token: str = None,
    telegram_chat_id: str = None,
    check_interval: int = 30
) -> MT5HealthCheck:
    """
    Create and configure a health monitor with optional Telegram notifications
    
    Args:
        login: MT5 account login
        password: MT5 account password
        server: MT5 broker server
        telegram_token: Optional Telegram bot token for notifications
        telegram_chat_id: Optional Telegram chat ID for notifications
        check_interval: Seconds between health checks
    
    Returns:
        Configured MT5HealthCheck instance (not started)
    """
    callbacks = {}
    
    if telegram_token and telegram_chat_id:
        on_disconnect, on_reconnect, on_failure = HealthCheckCallbacks.telegram_notify(
            telegram_token, telegram_chat_id
        )
        callbacks = {
            'on_disconnect': on_disconnect,
            'on_reconnect': on_reconnect,
            'on_failure': on_failure
        }
    
    health_check = MT5HealthCheck(
        check_interval=check_interval,
        **callbacks
    )
    
    health_check.set_credentials(login, password, server)
    
    return health_check


if __name__ == "__main__":
    # Test health check
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("Testing MT5 Health Check...")
    
    health_check = MT5HealthCheck(check_interval=10)
    
    # Single check
    is_healthy = health_check.check_connection()
    print(f"Connection healthy: {is_healthy}")
    
    # Get status
    status = health_check.get_status()
    print(f"Status: {status}")
