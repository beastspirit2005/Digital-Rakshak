from typing import Any, Dict
from backend.shared.contracts.runtime import IVoiceRuntime
import time
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

class RakshakVoiceRuntime(IVoiceRuntime):
    def __init__(self):
        self._model = None
        self._is_loaded = False
        
    def load(self):
        if not self._is_loaded:
            try:
                import whisper
                self._model = whisper.load_model("base")
                self._is_loaded = True
            except Exception as e:
                logger.warning(f"Failed to load Whisper: {e}")

    async def infer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        audio_path = payload.get("audio_path", "")
        if not os.path.exists(audio_path):
            raise ValueError("Audio file not found")
            
        start_time = time.time()
        
        # Local inference attempt
        try:
            self.load()
            if self._is_loaded and self._model:
                result = await asyncio.to_thread(self._model.transcribe, audio_path)
                transcript = result["text"]
                engine = "Rakshak-Whisper-Local"
            else:
                raise Exception("Whisper model not loaded.")
        except Exception as e:
            logger.warning(f"Local Whisper failed, falling back to Groq: {e}")
            from infrastructure.ai.groq_client import GroqClient
            groq = GroqClient()
            res = await groq.transcribe_audio(audio_path)
            transcript = res.get("transcript", "")
            engine = "Rakshak-Whisper-Groq"

        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "transcript": transcript,
            "execution_time_ms": execution_time_ms,
            "engine": engine,
            "version": "1.0"
        }

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._is_loaded else "unloaded"}
