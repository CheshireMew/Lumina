# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

backend_root = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(backend_root))

datas = []
binaries = []
build_target = os.environ.get('LUMINA_BUILD_TARGET', 'core')
main_provider_driver_modules = [
    'memory_postgres',
]
target_provider_driver_modules = {
    'core': main_provider_driver_modules,
    'stt-runtime': ['stt_sensevoice'],
    'tts-runtime': ['tts_edge'],
}.get(build_target, main_provider_driver_modules)
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


def _keep_cuda_runtime():
    return (
        build_target == 'stt-runtime'
        and os.environ.get('LUMINA_STT_ENABLE_CUDA', '1').lower() not in {'0', 'false', 'no'}
    )


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
    'provider_drivers',
    'app_config',
    'logger_setup',
    'main',
    'model_manager',
    'httpx',
    'h2',
    'hpack',
    'hyperframe',
    'pgvector.asyncpg',
    'pythonosc.udp_client',
]

hiddenimports += collect_submodules('services.managers')
hiddenimports += [
    'llm.drivers.deepseek_driver',
    'llm.drivers.gemini_driver',
    'llm.drivers.openai_driver',
    'llm.drivers.pollinations_driver',
]

# Collect application submodules.
for pkg in [
    'routers',
    'services',
    'pythonosc',
]:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

target_worker_runtimes = {
    'stt-runtime': ['capabilities.stt'],
    'tts-runtime': ['capabilities.tts'],
}.get(build_target, [])
for pkg in target_worker_runtimes:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

target_python_packages = {
    'stt-runtime': ['faster_whisper', 'sounddevice', 'soundfile', 'sherpa_onnx'],
    'tts-runtime': ['edge_tts'],
}.get(build_target, [])
for pkg in target_python_packages:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

if build_target == 'stt-runtime':
    hiddenimports += ['webrtcvad', '_webrtcvad']

target_excludes = {
    'core': [
        'faster_whisper',
        'webrtcvad',
        'sounddevice',
        'soundfile',
        'sherpa_onnx',
        'edge_tts',
        'provider_drivers.stt_sensevoice',
        'provider_drivers.tts_edge',
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
        'provider_drivers.tts_edge',
    ],
    'tts-runtime': [
        'faster_whisper',
        'webrtcvad',
        'sounddevice',
        'soundfile',
        'sherpa_onnx',
        'provider_drivers.stt_sensevoice',
    ],
}.get(build_target, [])

if not _keep_cuda_runtime():
    binaries = _drop_cuda_runtime(binaries)

if build_target == 'core':
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
    ('../../config/worker-runtimes.json', 'config'),
    ('../llm/drivers', 'llm/drivers'),
    ('../prompts', 'prompts'),
    ('../characters', 'characters'),
    ('../../public/live2d', 'assets/live2d'),
    ('../../public/libs', 'assets/libs'),
    ('../tts_emotion_styles.json', '.'),
]
if (backend_root / 'user_settings.json').exists():
    datas.append(('../user_settings.json', '.'))
for module_name in target_provider_driver_modules:
    datas.append((f'../provider_drivers/{module_name}', f'provider_drivers/{module_name}'))

block_cipher = None

a = Analysis(
    ['../backend_launcher.py'],
    pathex=['../'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['../hooks'],
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
        'provider_drivers.voiceauth_sherpa',
        'provider_drivers.voiceauth_sherpa.drivers',
        'provider_drivers.voiceauth_sherpa.drivers.voiceauth',
        'provider_drivers.voiceauth_sherpa.drivers.voiceauth.sherpa_cam_driver',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
if not _keep_cuda_runtime():
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
