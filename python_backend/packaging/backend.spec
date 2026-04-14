# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

backend_root = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / 'sdk'))

datas = []
binaries = []
build_target = os.environ.get('LUMINA_BUILD_TARGET', 'core-runtime')
main_extension_plugins = [
    'avatar_server',
    'emotion_broker',
    'hello_widget',
    'llm_core',
    'llm_deepseek',
    'llm_gemini',
    'llm_openai',
    'llm_pollinations',
    'memory_postgres',
    'search_brave',
    'search_duckduckgo',
]
target_extension_plugins = {
    'core-runtime': main_extension_plugins,
    'stt-runtime': ['stt_sensevoice'],
    'tts-runtime': ['tts_edge'],
}.get(build_target, main_extension_plugins)
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
    'routers',
    'services',
    'core',
    'plugins',
    'app_config',
    'logger_setup',
    'main',
    'model_manager',
    'httpx',
    'pgvector.asyncpg',
    'pythonosc.udp_client',
    'services.managers.llm_driver_plugins',
    'lumina',
]

hiddenimports += collect_submodules('services.managers')
hiddenimports += [
    'plugins.drivers.llm.deepseek_driver',
    'plugins.drivers.llm.gemini_driver',
    'plugins.drivers.llm.openai_driver',
    'plugins.drivers.llm.pollinations_driver',
]

# Collect all submodules for our packages
for pkg in [
    'routers',
    'services',
    'dependency_injector',
    'pythonosc',
    'lumina',
]:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

target_capability_packages = {
    'stt-runtime': ['capabilities.stt'],
    'tts-runtime': ['capabilities.tts'],
}.get(build_target, [])
for pkg in target_capability_packages:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

target_packages = {
    'stt-runtime': ['faster_whisper', 'webrtcvad', 'sounddevice', 'soundfile', 'sherpa_onnx'],
    'tts-runtime': ['edge_tts'],
}.get(build_target, [])
for pkg in target_packages:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

target_excludes = {
    'core-runtime': [
        'faster_whisper',
        'webrtcvad',
        'sounddevice',
        'soundfile',
        'sherpa_onnx',
        'edge_tts',
        'plugins.extensions.stt_sensevoice',
        'plugins.extensions.tts_edge',
        'plugins.extensions.voiceprint',
        'capabilities.stt',
        'capabilities.tts',
        'capabilities.vision',
        'services.managers.stt',
        'services.managers.tts',
        'services.managers.audio',
        'services.managers.audio_devices',
        'services.managers.vad_processor',
    ],
    'stt-runtime': [
        'edge_tts',
        'plugins.extensions.tts_edge',
        'plugins.extensions.voiceprint',
    ],
    'tts-runtime': [
        'faster_whisper',
        'webrtcvad',
        'sounddevice',
        'soundfile',
        'sherpa_onnx',
        'plugins.extensions.stt_sensevoice',
        'plugins.extensions.voiceprint',
    ],
}.get(build_target, [])

binaries = _drop_cuda_runtime(binaries)

if build_target == 'core-runtime':
    core_forbidden_fragments = [
        'capabilities/stt',
        'capabilities\\stt',
        'capabilities/tts',
        'capabilities\\tts',
        'capabilities/vision',
        'capabilities\\vision',
        'services/managers/stt.py',
        'services\\managers\\stt.py',
        'services/managers/tts.py',
        'services\\managers\\tts.py',
        'services/managers/audio.py',
        'services\\managers\\audio.py',
        'services/managers/audio_devices.py',
        'services\\managers\\audio_devices.py',
        'services/managers/vad_processor.py',
        'services\\managers\\vad_processor.py',
    ]

    def _is_core_forbidden(entry):
        combined = ' '.join(str(part).lower() for part in entry)
        return any(fragment in combined for fragment in core_forbidden_fragments)

    datas = [entry for entry in datas if not _is_core_forbidden(entry)]
    binaries = [entry for entry in binaries if not _is_core_forbidden(entry)]
    hiddenimports = [
        item for item in hiddenimports
        if item not in {
            'capabilities.stt',
            'capabilities.tts',
            'capabilities.vision',
            'services.managers.stt',
            'services.managers.tts',
            'services.managers.audio',
            'services.managers.audio_devices',
            'services.managers.vad_processor',
        }
    ]

# Add config files and prompts
datas += [
    ('../config', 'config'),
    ('../../config/capability-packages.json', 'config'),
    ('../plugins/drivers', 'plugins/drivers'),
    ('../prompts', 'prompts'),
    ('../sdk', 'sdk'),
    ('../tts_emotion_styles.json', '.'),
    ('../user_settings.json', '.'),
    ('../audio_config.json', '.'),
    ('../memory_config.json', '.'),
    ('../core_profile.json', '.'),
]
for plugin_name in target_extension_plugins:
    datas.append((f'../plugins/extensions/{plugin_name}', f'plugins/extensions/{plugin_name}'))

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
    excludes=[
        'tkinter',
        'unittest',
        'test',
        'pytest',
        'matplotlib',
        'pandas',
        'pyarrow',
        'scipy',
        *target_excludes,
        'torch',
        'torchaudio',
        'torchvision',
        'sentence_transformers',
        'transformers',
        'cv2',
        'llvmlite',
        'numba',
        'modelscope',
        'plugins.extensions.voiceauth_sherpa',
        'plugins.extensions.voiceauth_sherpa.drivers',
        'plugins.extensions.voiceauth_sherpa.drivers.voiceauth',
        'plugins.extensions.voiceauth_sherpa.drivers.voiceauth.sherpa_cam_driver',
    ],
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
