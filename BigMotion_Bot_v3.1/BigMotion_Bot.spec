# -*- mode: python ; coding: utf-8 -*-
"""
BigMotion Trading Bot - Production .spec File
Optimized for xgboost + lightgbm (no catboost)

Usage:
    pyinstaller BigMotion_Bot.spec
"""

import os
import sys
from pathlib import Path

block_cipher = None

# ==================================================================
# FIND ML LIBRARY DLLs (xgboost + lightgbm)
# ==================================================================
def find_ml_binaries():
    """Find xgboost and lightgbm DLL files"""
    binaries = []
    
    # XGBoost - Main ML library
    try:
        import xgboost
        xgb_path = Path(xgboost.__file__).parent
        xgb_dll = xgb_path / 'lib' / 'xgboost.dll'
        if xgb_dll.exists():
            # CRITICAL: Destination must be xgboost/lib/ (not '.')
            binaries.append((str(xgb_dll), 'xgboost/lib'))
            print(f"  ✅ XGBoost: {xgb_dll.name} ({xgb_dll.stat().st_size // (1024*1024)} MB)")
        else:
            print(f"  ⚠️  XGBoost DLL not found at {xgb_dll}")
    except ImportError:
        print("  ❌ XGBoost not installed - ML predictions will not work!")
    
    # LightGBM - Fast gradient boosting
    try:
        import lightgbm
        lgb_path = Path(lightgbm.__file__).parent
        for dll_file in lgb_path.rglob('*.dll'):
            binaries.append((str(dll_file), 'lightgbm/lib'))
            print(f"  ✅ LightGBM: {dll_file.name}")
    except ImportError:
        print("  ⚠️  LightGBM not installed (optional)")
    
    # CatBoost - SKIPPED (requires Visual Studio compiler)
    # Not needed - xgboost + lightgbm are sufficient!
    
    return binaries

# ==================================================================
# BUILD CONFIGURATION
# ==================================================================
print("\n" + "="*70)
print("🚀 BIGMOTION AUTOFX v3 - PRODUCTION BUILD")
print("="*70)
print("\nScanning for ML libraries (xgboost + lightgbm)...")
ml_binaries = find_ml_binaries()

if ml_binaries:
    print(f"\n✅ Found {len(ml_binaries)} ML library DLL files")
    print("   Ready for professional distribution!")
else:
    print("\n⚠️  No ML DLLs found - bot will use technical indicators only")

print("="*70 + "\n")

# ==================================================================
# Main Analysis
# ==================================================================
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ml_binaries,  # XGBoost + LightGBM DLLs
    datas=[
        # Include models folder
        ('models', 'models') if os.path.exists('models') else ([], 'models'),
        # Include icon if exists
        ('icon.ico', '.') if os.path.exists('icon.ico') else ([], '.'),
    ],
    hiddenimports=[
        # Core packages
        'MetaTrader5',
        'pandas',
        'numpy',
        'requests',
        'reportlab',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'dotenv',
        
        # Machine Learning (xgboost + lightgbm)
        'sklearn',
        'sklearn.ensemble',
        'sklearn.tree',
        'sklearn.linear_model',
        'sklearn.preprocessing',
        'xgboost',
        'xgboost.core',
        'xgboost.sklearn',
        'xgboost.training',
        'xgboost.compat',
        'xgboost.callback',
        'lightgbm',
        'lightgbm.sklearn',
        'lightgbm.basic',
        'lightgbm.engine',
        # catboost removed - not needed!
        
        # SciPy
        'scipy',
        'scipy.sparse',
        'scipy.sparse.csgraph',
        'scipy.sparse._csr',
        'scipy.special',
        'scipy.special._ufuncs_cxx',
        
        # Matplotlib
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends',
        'matplotlib.backends.backend_agg',
        
        # Pyparsing
        'pyparsing',
        'pyparsing.testing',
        
        # Telegram
        'telegram',
        'telegram.ext',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'catboost',  # Explicitly exclude catboost
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ==================================================================
# Executable Configuration
# ==================================================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BigMotion_Trading_Bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)

# ==================================================================
# Build Summary
# ==================================================================
print("\n" + "="*70)
print("✅ BUILD CONFIGURATION COMPLETE")
print("="*70)
print(f"  ML Libraries: xgboost + lightgbm")
print(f"  ML DLLs: {len(ml_binaries)} files included")
print(f"  Icon: {'Yes' if os.path.exists('icon.ico') else 'No'}")
print(f"  Version Info: {'Yes' if os.path.exists('version_info.txt') else 'No'}")
print(f"  Output: BigMotion_Trading_Bot.exe")
print(f"  Size: ~100-110 MB (optimized)")
print("="*70 + "\n")
