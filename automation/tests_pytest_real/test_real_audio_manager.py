"""
REAL integration test for AudioManager.
Tests VAD logic, state transitions, and callback handling.
"""
import sys
import os
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.audio_manager import AudioManager

@pytest.fixture
def audio_manager():
    # Mock callbacks
    on_start = MagicMock()
    on_end = MagicMock()
    on_vad = MagicMock()
    
    am = AudioManager(
        on_speech_start=on_start,
        on_speech_end=on_end,
        on_vad_status_change=on_vad
    )
    return am, on_start, on_end, on_vad

def test_audio_manager_init(audio_manager):
    am, _, _, _ = audio_manager
    assert am.sample_rate == 16000
    assert not am.is_speaking
    assert not am.is_running

def test_process_frame_silence(audio_manager):
    am, on_start, on_end, on_vad = audio_manager
    
    # 1. Provide silent frame (all zeros)
    silent_frame = np.zeros(am.frame_size, dtype=np.float32)
    result = am._process_frame(silent_frame)
    
    assert result == "silence"
    assert not am.is_speaking
    on_start.assert_not_called()

def test_process_frame_transition_to_speech(audio_manager):
    am, on_start, on_end, on_vad = audio_manager
    
    # Simulate speech frames (sine wave with energy)
    t = np.linspace(0, 0.03, am.frame_size)
    speech_frame = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # Fill sliding window to trigger Start threshold (0.8)
    for _ in range(am.window_size):
        result = am._process_frame(speech_frame)
        
    assert am.is_speaking
    # Note: _process_frame returns "speech_start" exactly once
    # but we filled it multiple times. The first few might be silence until threshold met.
    assert any(am.is_speaking for _ in range(am.window_size))

def test_audio_manager_stop_cleanup(audio_manager):
    am, _, _, _ = audio_manager
    am.is_running = True
    am.is_speaking = True
    am.audio_frames = [np.zeros(am.frame_size)]
    
    am.stop()
    
    assert not am.is_running
    assert not am.is_speaking
    assert len(am.audio_frames) == 0
