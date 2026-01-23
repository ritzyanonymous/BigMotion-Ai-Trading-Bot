# -*- mode: python ; coding: utf-8 -*-
"""
BigMotion Trading Bot - PyInstaller Spec File
Bundles the entire bot into a single executable (.exe)

Usage:
    pyinstaller BigMotion_Bot.spec

This creates a standalone .exe in the 'dist' folder that includes:
- All Python code (protected/obfuscated)
- All dependencies
- License system
- No source code exposed!
"""

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include config template
        ('config.json', '.'),
        # Include models folder
        ('models', 'models'),
        # Include any other data files
    ],
    hiddenimports=[
        'MetaTrader5',
        'pandas',
        'numpy',
        'sklearn',
        'sklearn.ensemble',
        'reportlab',
        'requests',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    upx=True,  # Compress the executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False for windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # Add your icon file
    version_file='version_info.txt',  # Add version info
)

# Optional: Create a one-folder bundle instead
# Uncomment for debugging or if one-file is too slow
"""
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BigMotion_Trading_Bot'
)
"""
