"""
BigMotion AutoFX Trading Bot v3.0
Complete AI-Powered Forex Trading System

Copyright (c) 2026 BigMotion AutoFX
Website: https://bigmotionautofx.com
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    """Main entry point with setup wizard integration"""
    
    print("\n" + "=" * 70)
    print("  🤖 BIGMOTION AUTOFX TRADING BOT v3.0")
    print("=" * 70 + "\n")
    
    try:
        # Import setup wizard
        from utils.setup_wizard import run_setup_wizard, needs_setup
        
        # Check if setup is needed
        if needs_setup():
            print("=" * 60)
            print("  🔧 FIRST TIME SETUP REQUIRED")
            print("=" * 60)
            print("\nNo valid configuration found.")
            print("Running interactive setup wizard...\n")
            
            # Run setup wizard
            if not run_setup_wizard():
                print("\n❌ Setup was not completed.")
                print("The bot cannot start without configuration.")
                input("\nPress Enter to exit...")
                sys.exit(1)
            
            print("\n" + "=" * 60)
            print("  ✅ SETUP COMPLETE!")
            print("=" * 60)
            print("\nConfiguration has been saved successfully.")
            print("The bot will now start...\n")
            input("Press Enter to continue...")
        
        # Import and run the proven trading bot
        from main_trading_engine import run_trading_bot
        run_trading_bot()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n💀 FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()
