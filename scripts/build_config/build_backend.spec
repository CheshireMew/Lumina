# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import sys
import os

block_cipher = None

# Base Directory (Project Root)
PROJECT_DIR = os.getcwd()
BACKEND_DIR = os.path.join(PROJECT_DIR, 'python_backend')

# --- Collection Logic ---
datas = []
binaries = []
hiddenimports = [
    'uvicorn.logging', 
    'uvicorn.loops', 
    'uvicorn.loops.auto', 
    'uvicorn.protocols', 
    'uvicorn.protocols.http', 
    'uvicorn.protocols.http.auto', 
    'uvicorn.lifespan', 
    'uvicorn.lifespan.on',
    'app_config',
    'main',
    'engineio.async_drivers.aiohttp', # for socketio/engineio
]

# Collect Sherpa ONNX (via hook, but also ensuring here if needed)
# tmp_ret = collect_all('sherpa_onnx')
# datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Collect Langchain
hiddenimports += collect_submodules('langchain')

# Config Files to Bundle
# (Source, Dest)
datas += [
    (os.path.join(BACKEND_DIR, 'stt_config.json'), '.'),
    (os.path.join(PROJECT_DIR, 'config', 'worker-runtimes.json'), 'config'),
    (os.path.join(BACKEND_DIR, 'tts_emotion_styles.json'), '.'),
    # (os.path.join(BACKEND_DIR, 'assets'), 'assets'), # Only if exists
    (os.path.join(BACKEND_DIR, 'schemas'), 'schemas'), # Schemas
    (os.path.join(BACKEND_DIR, 'tools'), 'tools'), # Tools
    (os.path.join(BACKEND_DIR, 'characters'), 'characters'), # Character Data
    # (os.path.join(BACKEND_DIR, 'voiceprint_profiles'), 'voiceprint_profiles'), # Optional
]

# Excludes to save space
excludes = [
    'tkinter', 'test', 'unittest', 'matplotlib', 
    'scipy', 'pandas',  # If not used
    'faster_whisper',
    'webrtcvad',
    'sounddevice',
    'soundfile',
    'sherpa_onnx',
    'edge_tts',
    'torch',
    'torchaudio',
    'torchvision',
    'sentence_transformers',
    'transformers',
    'cv2',
    'llvmlite',
    'numba',
    'modelscope',
    'capability_modules.voiceauth_sherpa',
    'capability_modules.voiceauth_sherpa.drivers',
    'capability_modules.voiceauth_sherpa.drivers.voiceauth',
    'capability_modules.voiceauth_sherpa.drivers.voiceauth.sherpa_cam_driver',
]

a = Analysis(
    [os.path.join(BACKEND_DIR, 'backend_launcher.py')],
    pathex=[BACKEND_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[os.path.join(BACKEND_DIR, 'hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='lumina_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Keep console for debug logging in Lite mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lumina_backend',
)
