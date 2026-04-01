# BigMotion AI Trading Bot v2 - Enhanced Edition

MT5 Auto-Trading Bot with Multi-TP Strategy, Comprehensive Logging, Health Monitoring, and Auto-Restart.

## 🆕 New Features

### 1. 🔍 Startup Diagnostics
Before the bot starts, it runs comprehensive checks:
- Python version compatibility
- Required packages installed
- Directory structure
- Config file validation
- Telegram connectivity
- MT5 terminal connection
- MT5 login credentials
- ML model availability
- Network connectivity
- Disk space
- File permissions

### 2. 🏥 MT5 Health Monitoring
Continuous monitoring of MT5 connection:
- Checks connection every 30 seconds
- Auto-detects disconnections
- Automatic reconnection (up to 5 attempts)
- Telegram notifications on disconnect/reconnect
- Tracks uptime and downtime metrics

### 3. 🐕 Watchdog Auto-Restart
External process monitor that:
- Monitors the bot process
- Automatically restarts on crash
- Configurable restart limits (default: 10 per hour)
- Cooldown between restarts (default: 60 seconds)
- Telegram notifications on restart
- Persists state across restarts

### 4. 📝 Comprehensive Logging
Every action is now logged with:
- Timestamp and source file/line number
- Clear emoji markers for quick scanning
- Detailed trade execution logs
- Error tracebacks for debugging

---

## 🚀 How to Run

### Option 1: Direct Run (No Auto-Restart)
```bash
python main.py
```

### Option 2: With Watchdog (Recommended for Production)
```bash
python watchdog.py
```

### Option 3: Run Diagnostics Only
```bash
python -m utils.diagnostics
```

---

## ⚙️ Watchdog Options

```bash
python watchdog.py --help

Options:
  --script         Bot script to run (default: main.py)
  --max-restarts   Max restarts per window (default: 10)
  --cooldown       Seconds between restarts (default: 60)
  --window         Restart window in seconds (default: 3600)
  --check-interval Health check interval (default: 30)
```

Example with custom settings:
```bash
python watchdog.py --max-restarts 5 --cooldown 120 --window 1800
```

---

## 📁 File Structure

```
BigMotion_Bot_v2/
├── main.py                  # Main bot (enhanced with logging)
├── watchdog.py              # Auto-restart wrapper
├── config.json              # Configuration (create from template)
├── requirements.txt         # Python dependencies
├── .gitignore
│
├── utils/
│   ├── __init__.py
│   ├── config.py            # Configuration loader
│   ├── diagnostics.py       # 🆕 Startup diagnostics
│   ├── health_check.py      # 🆕 MT5 health monitoring
│   ├── indicators.py        # Technical indicators
│   ├── logger.py            # Trade logging
│   ├── ml_predictor.py      # ML model interface
│   ├── position_manager.py  # Position tracking
│   ├── state_manager.py     # Bot state persistence
│   ├── telegram_report.py   # Telegram notifications
│   └── daily_report.py      # PDF report generator
│
├── models/                  # ML models
│   └── trading_model.pkl
│
├── data/logs/              # Trade logs
│   └── trades.csv
│
└── reports/                # Generated reports
```

---

## 📋 Log Files

| File | Description |
|------|-------------|
| `trading_bot.log` | Main bot activity log |
| `watchdog.log` | Watchdog process log |
| `bot_state.json` | Bot state persistence |
| `watchdog_state.json` | Watchdog state persistence |
| `data/logs/trades.csv` | Trade history |

---

## 🔧 Configuration

Create `config.json`:
```json
{
    "telegram_token": "YOUR_BOT_TOKEN",
    "telegram_chat_id": "YOUR_CHAT_ID",
    "mt5_login": "",
    "mt5_password": "",
    "mt5_server": "",
    "loop_interval": 60,
    "trading_pairs": ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"],
    "timeframe": "H1",
    "risk_per_trade": 0.9,
    "max_trades_per_day": 3,
    "max_daily_loss": 5.0,
    "max_open_positions": 5,
    "min_ml_confidence": 0.65,
    "tp_splits": [0.40, 0.30, 0.30],
    "ml_model_path": "models/trading_model.pkl"
}
```

Or use environment variables:
```bash
set TELEGRAM_BOT_TOKEN=your_token
set TELEGRAM_CHAT_ID=your_chat_id
set MT5_LOGIN=your_login
set MT5_PASSWORD=your_password
set MT5_SERVER=your_server
```

---

## 📊 Sample Log Output

```
2024-01-15 09:00:00 - __main__ - INFO - ======================================================================
2024-01-15 09:00:00 - __main__ - INFO - 🤖 MT5 TRADING BOT STARTING
2024-01-15 09:00:00 - __main__ - INFO - 📅 Start Time: 2024-01-15 09:00:00
2024-01-15 09:00:00 - __main__ - INFO - 🖥️  Platform: win32
2024-01-15 09:00:00 - __main__ - INFO - ======================================================================
2024-01-15 09:00:01 - __main__ - INFO - 📦 Loading dependencies...
2024-01-15 09:00:01 - __main__ - INFO -    ✅ MetaTrader5
2024-01-15 09:00:01 - __main__ - INFO -    ✅ pandas
...
2024-01-15 09:00:05 - __main__ - INFO - ✅ BOT INITIALIZATION COMPLETE
2024-01-15 09:00:05 - __main__ - INFO -    🎯 Multi-TP Strategy: [0.4, 0.3, 0.3]
2024-01-15 09:00:05 - __main__ - INFO -    📈 Min ML Confidence: 0.65
```

---

## 🛡️ Troubleshooting

### Bot won't start
1. Run diagnostics: `python -m utils.diagnostics`
2. Check `trading_bot.log` for errors
3. Verify MT5 is running and logged in

### Connection drops
- The health monitor will auto-reconnect
- Check `trading_bot.log` for reconnection attempts
- Verify your internet connection

### Too many restarts
- Watchdog stops after 10 restarts/hour by default
- Check logs to find the root cause
- Adjust limits if needed: `--max-restarts 20`

---

## 📞 Telegram Notifications

The bot sends notifications for:
- ✅ Bot started
- 🤖 Trade opened (with TP levels)
- ✅/❌ Trade closed (TP hit / SL hit)
- 📊 Daily report (with PDF)
- 🔴 MT5 disconnected
- 🟢 MT5 reconnected
- 🔄 Bot restart (from watchdog)
- 🛑 Critical errors

---

## 🔒 Security Notes

- Never commit `config.json` with credentials
- Use environment variables in production
- Keep `bot_state.json` and logs secure
- The `.gitignore` excludes sensitive files

---

## 📈 Performance Tips

1. **Use the Watchdog** for production - it ensures 24/7 uptime
2. **Monitor the logs** regularly for anomalies
3. **Set up Windows Task Scheduler** to start watchdog on boot
4. **VPS**: Schedule weekly restarts to clear memory leaks

---

*Enhanced by Claude - January 2025*
