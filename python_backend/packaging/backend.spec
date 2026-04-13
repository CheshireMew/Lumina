# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

backend_root = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / 'sdk'))

datas = []
binaries = []
cuda_binary_prefixes = (
    'cublas',
    'cudart',
    'cudnn',
    'cufft',
    'cupti',
    'curand',
    'cusolver',
    'cusparse',
    'nv',
)
cuda_binary_names = {
    'c10_cuda.dll',
    'caffe2_nvrtc.dll',
    'torch_cuda.dll',
}


def _drop_cuda_runtime(entries):
    filtered = []
    for entry in entries:
        target_name = Path(entry[0]).name.lower()
        source_name = Path(entry[1]).name.lower() if len(entry) > 1 else ''
        names = (target_name, source_name)
        if any(name in cuda_binary_names for name in names):
            continue
        if any(name.startswith(cuda_binary_prefixes) and name.endswith('.dll') for name in names):
            continue
        filtered.append(entry)
    return filtered


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
    'capabilities',
    'app_config',
    'logger_setup',
    'main',
    'model_manager',
    'httpx',
    'pgvector.asyncpg',
    'pythonosc.udp_client',
    'services.managers.llm_driver_plugins',
    'edge_tts',
    'lumina',
]

hiddenimports += collect_submodules('services.managers')

# Collect all submodules for our packages
for pkg in [
    'routers',
    'services',
    'capabilities',
    'plugins',
    'dependency_injector',
    'pgvector',
    'pythonosc',
    'edge_tts',
    'lumina',
]:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

binaries = _drop_cuda_runtime(binaries)

# Add config files and prompts
datas += [
    ('../config', 'config'),
    ('../plugins', 'plugins'),
    ('../prompts', 'prompts'),
    ('../sdk', 'sdk'),
    ('../../public/live2d', 'live2d'),
    ('../tts_emotion_styles.json', '.'),
    ('../user_settings.json', '.'),
    ('../audio_config.json', '.'),
    ('../memory_config.json', '.'),
    ('../core_profile.json', '.'),
]

block_cipher = None

a = Analysis(
    ['../backend_launcher.py'],
    pathex=['../'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
a.binaries = _drop_cuda_runtime(a.binaries)
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
