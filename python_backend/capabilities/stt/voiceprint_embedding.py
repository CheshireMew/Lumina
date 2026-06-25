import asyncio
import base64
import os
import tempfile

import numpy as np
import soundfile as sf
from fastapi import HTTPException, UploadFile

from .runtime_state import SttRuntimeState


class VoiceprintEmbeddingService:
    def __init__(self, state: SttRuntimeState):
        self._state = state

    async def generate(self, audio: UploadFile) -> dict:
        manager = self._state.voiceprint_manager
        if not manager:
            raise HTTPException(status_code=503, detail="Voiceprint driver not loaded")
        await manager.ensure_driver_loaded()

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                content = await audio.read()
                tmp.write(content)
                tmp_path = tmp.name

            audio_data, sample_rate = sf.read(tmp_path)
            if audio_data.ndim > 1:
                audio_data = audio_data[:, 0]

            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(
                None,
                manager.driver.extract_embedding,
                audio_data,
                sample_rate,
            )
            if embedding is None or embedding.size == 0:
                raise HTTPException(500, "Failed to extract embedding")

            embedding_b64 = base64.b64encode(embedding.astype(np.float32).tobytes()).decode("utf-8")
            return {"embedding": embedding_b64, "dims": len(embedding)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
