from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from infrastructure.osint.scanner import OSINTScanner
from infrastructure.graph.neo4j_client import IntelligenceGraph
from pydantic import BaseModel

from infrastructure.ai.ml_client import RakshakCoreClient
from api.deps import get_current_user
from domain.models.user import User

router = APIRouter(prefix="/scan", tags=["scan"])

# Globally load PyTorch model for instant scanning (Lazy initialization)
ml_client = RakshakCoreClient(model_version="1.0")
ml_client_loaded = False

class ScanResponse(BaseModel):
    is_safe: bool
    risk_level: str
    reasons: list[str]

class ScanRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    phone: Optional[str] = None
    upi: Optional[str] = None

@router.post("", response_model=ScanResponse)
async def live_prevention_scan(
    payload: ScanRequest,
    user: User = Depends(get_current_user)
):
    text = payload.text
    url = payload.url
    phone = payload.phone
    upi = payload.upi
    """
    Live Prevention Shield API.
    Used by browser extensions, mobile apps, or citizens to instantly check if an entity is safe.
    """
    global ml_client_loaded
    if not any([text, url, phone, upi]):
        raise HTTPException(status_code=400, detail="Must provide at least one parameter to scan (text, url, phone, or upi).")
        
    is_safe = True
    risk_level = "LOW"
    reasons = []
    
    # 0. Native AI Zero-Day Analysis
    if text or url:
        if not ml_client_loaded:
            ml_client.load_model()
            ml_client_loaded = True
            
        payload_to_scan = text if text else url
        
        # Check if PyTorch failed to load (running in Vercel Serverless Lite Mode)
        if not getattr(ml_client, 'model', None):
            # Fallback to Groq Llama-3 8B (extremely fast inference for Prevention Suite)
            try:
                from infrastructure.ai.groq_client import GroqClient
                groq = GroqClient()
                groq_res = await groq.analyze(
                    prompt=f"Is this text or URL a scam? Answer yes or no, and classify it. Payload: '{payload_to_scan}'", 
                    context={}, 
                    model_name="llama3-8b-8192"
                )
                
                confidence = float(groq_res.get("score", 0.0))
                threat_class = groq_res.get("decision", "Unknown")
                
                if confidence > 0.6 and "safe" not in threat_class.lower():
                    is_safe = False
                    risk_level = "CRITICAL"
                    reasons.append(f"Cloud AI Zero-Day Detection: {threat_class} ({confidence*100:.1f}% confidence).")
            except Exception as e:
                print(f"Groq fallback failed: {e}")
                # Silently degrade to OSINT/Neo4j graph rules to avoid blocking the user
                pass
        else:
            ai_res = ml_client.predict(payload_to_scan)
            
            if ai_res["confidence"] > 0.6 and ai_res["threat_class"] != "Safe":
                is_safe = False
                risk_level = "CRITICAL"
                reasons.append(f"Native AI Zero-Day Detection: {ai_res['threat_class']} ({ai_res['confidence']*100:.1f}% confidence).")
                if ai_res.get("behaviors"):
                    reasons.append(f"Attack DNA detected: {', '.join(ai_res['behaviors'])}.")

    # 1. Check OSINT Static Rules (URLs/Keywords)
    scanner = OSINTScanner()
    if url:
        res = scanner.scan_text(url)
        if res["risk_level"] in ["HIGH", "CRITICAL"]:
            is_safe = False
            risk_level = res["risk_level"]
            for flag in res["flagged_urls"]:
                reasons.append(flag["threat"])
                
    elif text:
        res = scanner.scan_text(text)
        if res["risk_level"] in ["HIGH", "CRITICAL"]:
            is_safe = False
            risk_level = res["risk_level"]
            for flag in res["flagged_urls"]:
                reasons.append(flag["threat"])

    # 2. Check Graph Database for known malicious entities
    graph = IntelligenceGraph()
    try:
        if phone:
            related = await graph.get_related_cases("PhoneNumber", phone)
            if len(related) > 0:
                is_safe = False
                risk_level = "CRITICAL"
                reasons.append(f"Phone number is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
                
        if upi:
            related = await graph.get_related_cases("UPI_ID", upi)
            if len(related) > 0:
                is_safe = False
                risk_level = "CRITICAL"
                reasons.append(f"UPI ID is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
                
        if url:
            related = await graph.get_related_cases("URL", url)
            if len(related) > 0:
                is_safe = False
                risk_level = "CRITICAL"
                reasons.append(f"URL is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
    finally:
        await graph.close()
        
    return ScanResponse(
        is_safe=is_safe,
        risk_level=risk_level,
        reasons=reasons if not is_safe else ["No known threats found."]
    )

from fastapi import UploadFile, File

@router.post("/qr", response_model=ScanResponse)
async def live_prevention_scan_qr(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """
    Decodes an uploaded QR code and pipes its hidden payload (URL/UPI) directly into the Prevention Suite.
    """
    from infrastructure.osint.qr_decoder import QRDecoder
    import filetype
    decoder = QRDecoder()
    
    contents = await file.read()
    
    kind = filetype.guess(contents)
    if kind is None or kind.mime not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail=f"Invalid file signature for QR code. Expected image.")
        
    payload = decoder.decode_image(contents)
    
    if not payload:
        raise HTTPException(status_code=400, detail="No valid QR code found in the image.")
        
    # Pipe the hidden payload into the existing AI and OSINT pipeline
    # We will pass it as `text` so the native AI model parses the full intent
    return await live_prevention_scan(payload=ScanRequest(text=payload), user=user)

import os
import tempfile

@router.post("/apk", response_model=ScanResponse)
async def live_prevention_scan_apk(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """
    Scans an uploaded APK file for dangerous permissions using Androguard.
    """
    if not file.filename.endswith(".apk"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an APK.")
        
    contents = await file.read()
    import filetype
    kind = filetype.guess(contents)
    if kind is None or kind.mime not in ["application/vnd.android.package-archive", "application/zip", "application/java-archive"]:
        raise HTTPException(status_code=400, detail=f"Invalid file signature for APK.")
        
    # Androguard needs a file path, so we save it temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".apk") as temp_file:
        temp_file.write(contents)
        temp_path = temp_file.name

    is_safe = True
    risk_level = "LOW"
    reasons = []

    try:
        from androguard.core.bytecodes.apk import APK
        apk = APK(temp_path)
        permissions = apk.get_permissions()
        
        # Check for dangerous permissions commonly used by malware
        dangerous_perms = {
            "android.permission.BIND_ACCESSIBILITY_SERVICE": "Can read everything on your screen and control your device (Often used by banking trojans).",
            "android.permission.READ_SMS": "Can read your text messages, including OTPs.",
            "android.permission.RECEIVE_SMS": "Can intercept incoming SMS messages.",
            "android.permission.SYSTEM_ALERT_WINDOW": "Can draw overlays on top of other apps (Used for overlay attacks to steal credentials).",
            "android.permission.READ_CALL_LOG": "Can access your call history.",
            "android.permission.SEND_SMS": "Can send SMS messages without your knowledge (May incur charges).",
            "android.permission.REQUEST_INSTALL_PACKAGES": "Can install other unknown apps without permission."
        }
        
        found_dangerous = []
        for perm in permissions:
            if perm in dangerous_perms:
                found_dangerous.append(f"{perm.split('.')[-1]}: {dangerous_perms[perm]}")
                
        if found_dangerous:
            is_safe = False
            risk_level = "CRITICAL"
            reasons.append("Found dangerous permissions in this APK that are commonly abused by malware:")
            reasons.extend(found_dangerous)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse APK: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return ScanResponse(
        is_safe=is_safe,
        risk_level=risk_level,
        reasons=reasons if not is_safe else ["No dangerous permissions found. Code looks safe."]
    )

@router.post("/counterfeit")
async def scan_counterfeit_currency(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """
    Live Vision AI Pipeline for Counterfeit Currency Analysis.
    Pipes uploaded image directly to VisionAgent (Groq Cloud Mode or Local PyTorch).
    """
    import os
    import tempfile
    from domain.agents.vision_agent import VisionAgent
    
    contents = await file.read()
    import filetype
    kind = filetype.guess(contents)
    if kind is None or not kind.mime.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{kind.extension}") as temp_file:
        temp_file.write(contents)
        temp_path = temp_file.name

    try:
        agent = VisionAgent()
        result = await agent.execute(
            payload={"text": temp_path, "analyze_type": "counterfeit"},
            case_id="LIVE_SCAN"
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

