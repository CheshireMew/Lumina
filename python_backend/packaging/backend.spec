# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'engineio.async_drivers.asgi',
    'socketio.async_drivers.asgi',
    'routers',
    'services',
    'core',
    'plugins',
    'app_config',
    'logger_setup',
    'model_manager',
    'prompt_manager',
    'httpx',
]

# Collect all submodules for our packages
for pkg in ['routers', 'services', 'core', 'plugins']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

# Add config files and prompts
datas += [
    ('../config', 'config'),
    ('../prompts', 'prompts'),
    ('../stt_config.json', '.'),
    ('../tts_emotion_styles.json', '.'),
    ('../user_settings.json', '.'),
    ('../audio_config.json', '.'),
    ('../memory_config.json', '.'),
    ('../core_profile.json', '.'),
]

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=['../'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'email', 'http.server', 'xml.dom', 'xml.sax'],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lumina_backend',
)
