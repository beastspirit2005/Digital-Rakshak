import io
from typing import Optional
from pyzbar.pyzbar import decode
from PIL import Image

class QRDecoder:
    """
    Decodes QR codes from raw image bytes and extracts the hidden payload (URL, UPI ID, or Text).
    Used by the Quishing Prevention Suite.
    """
    
    def decode_image(self, image_bytes: bytes) -> Optional[str]:
        try:
            # Load image from bytes
            img = Image.open(io.BytesIO(image_bytes))
            
            # Decode QR codes
            decoded_objects = decode(img)
            
            if not decoded_objects:
                return None
                
            # Extract the first QR code payload
            payload = decoded_objects[0].data.decode('utf-8')
            return payload
            
        except Exception as e:
            print(f"Failed to decode QR code: {e}")
            return None
