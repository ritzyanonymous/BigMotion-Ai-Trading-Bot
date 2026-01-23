"""
Startup Diagnostics Module
Validates all dependencies and configurations before bot starts
"""
import os
import sys
import json
import socket
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class StartupDiagnostics:
    """Comprehensive startup diagnostics for the trading bot"""
    
    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []
        self.start_time = datetime.now()
    
    def log_result(self, check_name: str, passed: bool, message: str, level: str = "INFO"):
        """Log a diagnostic result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            'check': check_name,
            'passed': passed,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self.results.append(result)
        
        if not passed:
            if level == "ERROR":
                self.errors.append(result)
                logger.error(f"{status} | {check_name}: {message}")
            else:
                self.warnings.append(result)
                logger.warning(f"{status} | {check_name}: {message}")
        else:
            logger.info(f"{status} | {check_name}: {message}")
    
    def check_python_version(self) -> bool:
        """Check Python version compatibility"""
        version = sys.version_info
        passed = version.major == 3 and version.minor >= 8
        self.log_result(
            "Python Version",
            passed,
            f"Python {version.major}.{version.minor}.{version.micro}" + 
            (" (OK)" if passed else " (Requires 3.8+)"),
            "ERROR" if not passed else "INFO"
        )
        return passed
    
    def check_required_packages(self) -> bool:
        """Check if all required packages are installed"""
        required_packages = [
            ('MetaTrader5', 'MetaTrader5'),
            ('pandas', 'pandas'),
            ('numpy', 'numpy'),
            ('sklearn', 'scikit-learn'),
            ('reportlab', 'reportlab'),
            ('requests', 'requests'),
        ]
        
        all_passed = True
        missing = []
        
        for import_name, package_name in required_packages:
            try:
                __import__(import_name)
                self.log_result(f"Package: {package_name}", True, "Installed")
            except ImportError:
                all_passed = False
                missing.append(package_name)
                self.log_result(
                    f"Package: {package_name}",
                    False,
                    f"NOT INSTALLED - Run: pip install {package_name}",
                    "ERROR"
                )
        
        if missing:
            logger.error(f"Missing packages: {', '.join(missing)}")
            logger.error(f"Install with: pip install {' '.join(missing)}")
        
        return all_passed
    
    def check_directory_structure(self) -> bool:
        """Check and create required directories"""
        required_dirs = [
            'data/logs',
            'models',
            'reports'
        ]
        
        all_passed = True
        
        for dir_path in required_dirs:
            path = Path(dir_path)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    self.log_result(f"Directory: {dir_path}", True, "Created")
                except Exception as e:
                    all_passed = False
                    self.log_result(
                        f"Directory: {dir_path}",
                        False,
                        f"Failed to create: {e}",
                        "ERROR"
                    )
            else:
                self.log_result(f"Directory: {dir_path}", True, "Exists")
        
        return all_passed
    
    def check_config_file(self, config_path: str = 'config.json') -> Tuple[bool, Dict]:
        """Check configuration file"""
        config = {}
        
        if not Path(config_path).exists():
            self.log_result(
                "Config File",
                False,
                f"{config_path} not found - will create default",
                "WARNING"
            )
            return False, config
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.log_result("Config File", True, f"Loaded {config_path}")
        except json.JSONDecodeError as e:
            self.log_result(
                "Config File",
                False,
                f"Invalid JSON in {config_path}: {e}",
                "ERROR"
            )
            return False, config
        except Exception as e:
            self.log_result(
                "Config File",
                False,
                f"Error reading {config_path}: {e}",
                "ERROR"
            )
            return False, config
        
        return True, config
    
    def check_telegram_credentials(self, config: Dict) -> bool:
        """Check Telegram bot credentials"""
        token = os.getenv('TELEGRAM_BOT_TOKEN', config.get('telegram_token', ''))
        chat_id = os.getenv('TELEGRAM_CHAT_ID', config.get('telegram_chat_id', ''))
        
        if not token:
            self.log_result(
                "Telegram Token",
                False,
                "Missing - Set TELEGRAM_BOT_TOKEN env var or in config.json",
                "ERROR"
            )
            return False
        
        if not chat_id:
            self.log_result(
                "Telegram Chat ID",
                False,
                "Missing - Set TELEGRAM_CHAT_ID env var or in config.json",
                "ERROR"
            )
            return False
        
        # Test Telegram connectivity
        try:
            import requests
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    bot_name = bot_info.get('result', {}).get('username', 'Unknown')
                    self.log_result(
                        "Telegram Connection",
                        True,
                        f"Connected as @{bot_name}"
                    )
                    return True
            
            self.log_result(
                "Telegram Connection",
                False,
                f"Invalid token - Status: {response.status_code}",
                "ERROR"
            )
            return False
            
        except requests.exceptions.Timeout:
            self.log_result(
                "Telegram Connection",
                False,
                "Connection timeout - Check internet",
                "ERROR"
            )
            return False
        except Exception as e:
            self.log_result(
                "Telegram Connection",
                False,
                f"Error: {e}",
                "ERROR"
            )
            return False
    
    def check_mt5_installation(self) -> bool:
        """Check MT5 installation and connectivity"""
        try:
            import MetaTrader5 as mt5
            self.log_result("MT5 Package", True, "Imported successfully")
        except ImportError:
            self.log_result(
                "MT5 Package",
                False,
                "MetaTrader5 not installed",
                "ERROR"
            )
            return False
        
        # Try to initialize MT5
        try:
            if mt5.initialize():
                terminal_info = mt5.terminal_info()
                if terminal_info:
                    self.log_result(
                        "MT5 Terminal",
                        True,
                        f"Connected - Build {terminal_info.build}"
                    )
                    mt5.shutdown()
                    return True
                else:
                    mt5.shutdown()
                    self.log_result(
                        "MT5 Terminal",
                        False,
                        "Initialized but no terminal info",
                        "WARNING"
                    )
                    return True
            else:
                error = mt5.last_error()
                self.log_result(
                    "MT5 Terminal",
                    False,
                    f"Failed to initialize: {error}",
                    "ERROR"
                )
                return False
        except Exception as e:
            self.log_result(
                "MT5 Terminal",
                False,
                f"Exception: {e}",
                "ERROR"
            )
            return False
    
    def check_mt5_login(self, config: Dict) -> bool:
        """Check MT5 login credentials"""
        login = os.getenv('MT5_LOGIN', config.get('mt5_login', ''))
        password = os.getenv('MT5_PASSWORD', config.get('mt5_password', ''))
        server = os.getenv('MT5_SERVER', config.get('mt5_server', ''))
        
        if not all([login, password, server]):
            self.log_result(
                "MT5 Credentials",
                False,
                "Missing login/password/server in config or env vars",
                "WARNING"
            )
            return False
        
        try:
            import MetaTrader5 as mt5
            
            if not mt5.initialize():
                self.log_result(
                    "MT5 Login",
                    False,
                    "Cannot initialize MT5",
                    "ERROR"
                )
                return False
            
            if mt5.login(int(login), password, server):
                account_info = mt5.account_info()
                if account_info:
                    self.log_result(
                        "MT5 Login",
                        True,
                        f"Logged in - Account: {account_info.login}, Balance: {account_info.balance} {account_info.currency}"
                    )
                    mt5.shutdown()
                    return True
            
            error = mt5.last_error()
            mt5.shutdown()
            self.log_result(
                "MT5 Login",
                False,
                f"Login failed: {error}",
                "ERROR"
            )
            return False
            
        except Exception as e:
            self.log_result(
                "MT5 Login",
                False,
                f"Exception: {e}",
                "ERROR"
            )
            return False
    
    def check_ml_model(self, model_path: str = 'models/trading_model.pkl') -> bool:
        """Check ML model file"""
        if not Path(model_path).exists():
            self.log_result(
                "ML Model",
                False,
                f"{model_path} not found - Bot will use fallback logic",
                "WARNING"
            )
            return False
        
        try:
            import pickle
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            if 'model' in model_data:
                accuracy = model_data.get('accuracy', 'Unknown')
                model_name = model_data.get('model_name', 'Unknown')
                self.log_result(
                    "ML Model",
                    True,
                    f"Loaded - Type: {model_name}, Accuracy: {accuracy:.2%}" if isinstance(accuracy, float) else f"Loaded - Type: {model_name}"
                )
                return True
            else:
                self.log_result(
                    "ML Model",
                    False,
                    "Invalid model format - missing 'model' key",
                    "WARNING"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ML Model",
                False,
                f"Error loading model: {e}",
                "WARNING"
            )
            return False
    
    def check_network_connectivity(self) -> bool:
        """Check internet connectivity"""
        test_hosts = [
            ('Google DNS', '8.8.8.8', 53),
            ('Cloudflare', '1.1.1.1', 53),
        ]
        
        for name, host, port in test_hosts:
            try:
                socket.create_connection((host, port), timeout=5)
                self.log_result("Network", True, f"Connected via {name}")
                return True
            except (socket.timeout, socket.error):
                continue
        
        self.log_result(
            "Network",
            False,
            "No internet connection detected",
            "ERROR"
        )
        return False
    
    def check_disk_space(self, min_mb: int = 100) -> bool:
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            free_mb = free // (1024 * 1024)
            
            passed = free_mb >= min_mb
            self.log_result(
                "Disk Space",
                passed,
                f"{free_mb} MB available" + ("" if passed else f" (Need {min_mb} MB minimum)"),
                "WARNING" if not passed else "INFO"
            )
            return passed
        except Exception as e:
            self.log_result(
                "Disk Space",
                False,
                f"Error checking: {e}",
                "WARNING"
            )
            return True  # Don't block startup for this
    
    def check_file_permissions(self) -> bool:
        """Check write permissions for required files"""
        test_files = [
            'data/logs/test_write.tmp',
            'reports/test_write.tmp',
            'bot_state.json'
        ]
        
        all_passed = True
        
        for test_file in test_files:
            try:
                Path(test_file).parent.mkdir(parents=True, exist_ok=True)
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception as e:
                all_passed = False
                self.log_result(
                    f"Write Permission: {Path(test_file).parent}",
                    False,
                    f"Cannot write: {e}",
                    "ERROR"
                )
        
        if all_passed:
            self.log_result("File Permissions", True, "All directories writable")
        
        return all_passed
    
    def run_all_checks(self, config_path: str = 'config.json') -> Tuple[bool, Dict]:
        """Run all diagnostic checks"""
        logger.info("=" * 60)
        logger.info("🔍 RUNNING STARTUP DIAGNOSTICS")
        logger.info("=" * 60)
        
        # Run checks
        checks = {
            'python_version': self.check_python_version(),
            'packages': self.check_required_packages(),
            'directories': self.check_directory_structure(),
            'network': self.check_network_connectivity(),
            'disk_space': self.check_disk_space(),
            'file_permissions': self.check_file_permissions(),
        }
        
        # Config-dependent checks
        config_ok, config = self.check_config_file(config_path)
        checks['config'] = config_ok
        
        if config_ok or config:
            checks['telegram'] = self.check_telegram_credentials(config)
            checks['mt5_install'] = self.check_mt5_installation()
            if checks['mt5_install']:
                checks['mt5_login'] = self.check_mt5_login(config)
            checks['ml_model'] = self.check_ml_model(config.get('ml_model_path', 'models/trading_model.pkl'))
        
        # Summary
        elapsed = (datetime.now() - self.start_time).total_seconds()
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r['passed'])
        
        logger.info("=" * 60)
        logger.info(f"📊 DIAGNOSTIC SUMMARY ({elapsed:.2f}s)")
        logger.info(f"   Passed: {passed_checks}/{total_checks}")
        logger.info(f"   Errors: {len(self.errors)}")
        logger.info(f"   Warnings: {len(self.warnings)}")
        logger.info("=" * 60)
        
        # Critical checks that must pass
        critical_passed = all([
            checks.get('python_version', False),
            checks.get('packages', False),
            checks.get('directories', False),
            checks.get('network', False),
            checks.get('file_permissions', False),
        ])
        
        if self.errors:
            logger.error("❌ CRITICAL ERRORS - Bot may not function correctly:")
            for error in self.errors:
                logger.error(f"   • {error['check']}: {error['message']}")
        
        if self.warnings:
            logger.warning("⚠️  WARNINGS - Bot will run with limitations:")
            for warning in self.warnings:
                logger.warning(f"   • {warning['check']}: {warning['message']}")
        
        return critical_passed, {
            'checks': checks,
            'results': self.results,
            'errors': self.errors,
            'warnings': self.warnings,
            'elapsed_seconds': elapsed
        }


def run_diagnostics(config_path: str = 'config.json') -> Tuple[bool, Dict]:
    """Convenience function to run diagnostics"""
    diag = StartupDiagnostics()
    return diag.run_all_checks(config_path)


if __name__ == "__main__":
    # Configure logging for standalone run
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    passed, results = run_diagnostics()
    
    if passed:
        print("\n✅ All critical checks passed - Bot is ready to start")
    else:
        print("\n❌ Some critical checks failed - Please fix errors before starting bot")
        sys.exit(1)
