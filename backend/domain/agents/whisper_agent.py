import os
import asyncio
import logging

logger = logging.getLogger(__name__)

class WhisperAgent:
    Analyzes audio evidence (MP3, WAV) via local Whisper model.
    Falls back to Groq Audio if ffmpeg is not installed.
    """
    def __init__(self):
        self.model_name = "base"
        self._model = None
        
    def _load_model(self):
        if self._model is None:
            import whisper
            logger.info("Loading local Whisper model into memory...")
            self._model = whisper.load_model(self.model_name)
        return self._model

    async def execute(self, audio_path: str) -> dict:
        if not os.path.exists(audio_path):
            return {"error": "Audio file not found"}
            
        from core.config import settings
        
        if settings.DEFAULT_AI_MODE == "groq":
            try:
                from infrastructure.ai.groq_client import GroqClient
                groq = GroqClient()
                res = await groq.transcribe_audio(audio_path)
                if not "error" in res:
                    return res
            except Exception as e:
                logger.warning(f"Groq Whisper failed: {e}. Falling back to local.")
                
        # Try local whisper (or fallback to Gemini if missing ffmpeg)
        try:
            import whisper
            model = await asyncio.to_thread(self._load_model)
            # This requires ffmpeg installed. If it fails, we catch it.
            result = await asyncio.to_thread(model.transcribe, audio_path)
            transcript = result["text"]
            return {"transcript": transcript, "source": "local_whisper"}
        except Exception as e:
            logger.warning(f"Local Whisper failed (likely missing ffmpeg): {e}. Falling back to Groq Audio.")
            # Fallback to Groq
            return await self._groq_fallback(audio_path)
            
    async def _groq_fallback(self, audio_path: str) -> dict:
        try:
            from infrastructure.ai.groq_client import GroqClient
            groq = GroqClient()
            return await groq.transcribe_audio(audio_path)
        except Exception as e:
            return {"error": f"Audio transcription completely failed: {str(e)}"}
