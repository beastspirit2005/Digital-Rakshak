import os
import asyncio
import logging

logger = logging.getLogger(__name__)

class WhisperAgent:
    """
    Analyzes audio evidence (MP3, WAV) via local Whisper model.
    Falls back to Gemini Audio if ffmpeg is not installed.
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
            
        # Try local whisper first
        try:
            import whisper
            model = await asyncio.to_thread(self._load_model)
            # This requires ffmpeg installed. If it fails, we catch it.
            result = await asyncio.to_thread(model.transcribe, audio_path)
            transcript = result["text"]
            return {"transcript": transcript, "source": "local_whisper"}
        except Exception as e:
            logger.warning(f"Local Whisper failed (likely missing ffmpeg): {e}. Falling back to Gemini Audio.")
            # Fallback to Gemini
            return await self._gemini_fallback(audio_path)
            
    async def _gemini_fallback(self, audio_path: str) -> dict:
        try:
            from google import genai
            from google.genai import types
            from core.config import settings
            
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
                
            ext = os.path.splitext(audio_path)[1].lower().replace('.', '')
            mime_type = f"audio/{ext}" if ext in ["mp3", "wav", "m4a", "ogg", "flac"] else "audio/mp3"
            
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            
            prompt = "You are a transcription AI. Please transcribe exactly what is spoken in this audio file. Output nothing but the transcription."
            
            response = await client.aio.models.generate_content(
                model="gemini-1.5-flash",
                contents=[prompt, audio_part],
                config=types.GenerateContentConfig(temperature=0.1)
            )
            
            return {"transcript": response.text, "source": "gemini_audio_fallback"}
        except Exception as e:
            return {"error": f"Audio transcription completely failed: {str(e)}"}
