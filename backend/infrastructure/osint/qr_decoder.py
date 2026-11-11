import io
import os
import logging
import tempfile
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

# Resilient native library loading with graceful fallbacks
PYZBAR_AVAILABLE = False
try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except (ImportError, Exception):
    logger.debug("pyzbar not available or C-shared library missing; using fallback decoders.")

CV2_AVAILABLE = False
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except (ImportError, Exception):
    logger.debug("opencv not available; using PIL and Vision AI fallbacks.")


class QRDecoder:
    """
    Decodes QR codes from raw image bytes and extracts the hidden payload (URL, UPI ID, or Text).
    Implements multi-tiered fallback:
    1. pyzbar (fast native C decoding, sub-millisecond)
    2. OpenCV QRCodeDetector (if cv2 is installed)
    3. Vision AI Optical Extraction (Groq Vision / Gemini Flash)
    """

    def decode_image(self, image_bytes: bytes) -> Optional[str]:
        """Synchronously attempts local decoding using pyzbar or OpenCV."""
        # 1. Try pyzbar if available
        if PYZBAR_AVAILABLE:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                decoded_objects = decode(img)
                if decoded_objects:
                    return decoded_objects[0].data.decode('utf-8', errors='ignore')
            except Exception as e:
                logger.debug("pyzbar decode failed: %s", e)

        # 2. Try OpenCV QRCodeDetector if available
        if CV2_AVAILABLE:
            try:
                nparr = np.frombuffer(image_bytes, np.uint8)
                img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img_cv is not None:
                    detector = cv2.QRCodeDetector()
                    data, bbox, _ = detector.detectAndDecode(img_cv)
                    if data:
                        return data.strip()
            except Exception as e:
                logger.debug("OpenCV QR decode failed: %s", e)

        return None

    async def decode_image_async(self, image_bytes: bytes) -> Optional[str]:
        """
        Asynchronously decodes QR code, falling back to Vision AI if local C-libraries
        are unavailable or unable to resolve distorted optical matrices.
        """
        # 1. Try fast local decoding first
        payload = self.decode_image(image_bytes)
        if payload:
            return payload

        # 2. Vision AI fallback (Groq Qwen Vision / Gemini Flash)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            try:
                from domain.agents.vision_agent import VisionAgent
                agent = VisionAgent()
                result = await agent.execute(
                    payload={"text": tmp_path, "analyze_type": "scam"},
                    case_id="QR_OPTICAL_DECODE"
                )

                # Prioritize extracted URLs or UPI handles from vision analysis
                urls = result.get("urls", [])
                if urls:
                    return urls[0]

                upis = result.get("upi_ids", [])
                if upis:
                    return upis[0]

                extracted = result.get("extracted_text", "")
                if extracted and not extracted.startswith("Mock") and "Offline" not in extracted:
                    # Only accept if it resembles a valid URL, UPI handle, or verifiable data string
                    if any(marker in extracted.lower() for marker in ["http", "@", "upi:", "tel:"]):
                        return extracted.strip()

            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as exc:
            logger.debug("Vision AI QR fallback notice: %s", exc)

        return None
