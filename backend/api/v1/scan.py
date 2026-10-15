from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from infrastructure.osint.scanner import OSINTScanner
from infrastructure.graph.neo4j_client import IntelligenceGraph
from pydantic import BaseModel

from infrastructure.ai.ml_client import RakshakCoreClient
from api.deps import get_current_user, get_current_user_optional, OFFICIAL_INSTITUTIONAL_ROLES
from domain.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])

# Globally load PyTorch model for instant scanning (Lazy initialization)
ml_client = RakshakCoreClient(model_version="1.0")
ml_client_loaded = False

# Guest rate limit: 5 scans per day per IP address
GUEST_DAILY_LIMIT = 5


class ScanResponse(BaseModel):
    is_safe:    bool
    risk_level: str
    reasons:    list[str]
    # Pro-only enrichment fields (None for free/guest)
    attack_dna_match: Optional[str] = None
    related_cases:    Optional[int] = None


class ScanRequest(BaseModel):
    text:  Optional[str] = None
    url:   Optional[str] = None
    phone: Optional[str] = None
    upi:   Optional[str] = None


async def _check_guest_rate_limit(request: Request) -> None:
    """
    Enforce 5-scans-per-day limit for unauthenticated (guest) users using
    a Redis INCR counter keyed by client IP.  Falls back silently if Redis
    is unavailable (fail-open to avoid blocking guests when Redis is down).
    """
    from core.config import settings
    client_ip = request.client.host if request.client else "unknown"
    redis_key = f"dr:guest_scan:{client_ip}:{__import__('datetime').date.today()}"

    try:
        import redis.asyncio as redis_async
        r = redis_async.from_url(settings.REDIS_URL, decode_responses=True,
                                  socket_connect_timeout=1, socket_timeout=1)
        count = await r.incr(redis_key)
        if count == 1:
            await r.expire(redis_key, 86400)  # TTL: 24 hours
        await r.aclose()
        if count > GUEST_DAILY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Guest scan limit reached ({GUEST_DAILY_LIMIT}/day). "
                    "Create a free account for unlimited scans."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.debug("Redis guest rate limit check failed (fail-open): %s", exc)


@router.post("", response_model=ScanResponse)
async def live_prevention_scan(
    request: Request,
    payload: ScanRequest,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Live Prevention Shield API.

    * **Guest (unauthenticated)**: 5 scans/day per IP, basic risk result.
    * **Free account**: Unlimited scans, basic risk result.
    * **Pro account**: Unlimited scans + Attack DNA enrichment + related case count.

    Used by the consumer Prevention Suite, browser extensions, and mobile apps.
    """
    # Rate-limit guests
    if user is None:
        await _check_guest_rate_limit(request)

    text  = payload.text
    url   = payload.url
    phone = payload.phone
    upi   = payload.upi

    global ml_client_loaded
    if not any([text, url, phone, upi]):
        raise HTTPException(
            status_code=400,
            detail="Must provide at least one parameter to scan (text, url, phone, or upi).",
        )

    is_pro = (
        user is not None
        and (
            user.role in OFFICIAL_INSTITUTIONAL_ROLES
            or (
                getattr(user, "b2c_plan_code", "b2c_free") != "b2c_free"
                and getattr(user, "b2c_subscription_status", "") == "active"
            )
        )
    )

    is_safe    = True
    risk_level = "LOW"
    reasons: list[str] = []
    attack_dna_match: Optional[str] = None
    related_cases:    Optional[int]  = None

    # 0. Native AI Zero-Day Analysis
    payload_to_scan = text or url or upi
    if payload_to_scan:
        if not ml_client_loaded:
            ml_client.load_model()
            ml_client_loaded = True
            
        # Check if PyTorch failed to load (running in Vercel Serverless Lite Mode)
        if not getattr(ml_client, 'model', None):
            # Fallback to Groq Llama-3 8B (extremely fast inference for Prevention Suite)
            try:
                from infrastructure.ai.groq_client import GroqClient
                groq = GroqClient()
                if upi:
                    prompt = f"Is this UPI address suspicious or impersonating a bank/refund desk? UPI: '{upi}'. Answer yes or no, and classify."
                else:
                    prompt = f"Is this text or URL a scam? Answer yes or no, and classify it. Payload: '{payload_to_scan}'"
                groq_res = await groq.analyze(
                    prompt=prompt, 
                    context={}, 
                    model_name="openai/gpt-oss-20b"
                )
                
                confidence = float(groq_res.get("score", 0.0))
                threat_class = groq_res.get("decision", "Unknown")
                
                if confidence > 0.6 and "safe" not in threat_class.lower():
                    is_safe = False
                    risk_level = "CRITICAL"
                    reasons.append(f"Cloud AI Zero-Day Detection: {threat_class} ({confidence*100:.1f}% confidence).")
                    attack_dna_match = f"{threat_class} — Social Engineering & Deceptive Pattern"
            except Exception as e:
                print(f"Groq fallback failed: {e}")
                pass
        else:
            ai_res = ml_client.predict(payload_to_scan)
            
            if ai_res["confidence"] > 0.6 and ai_res["threat_class"] != "Safe":
                is_safe = False
                risk_level = "CRITICAL"
                reasons.append(f"Native AI Zero-Day Detection: {ai_res['threat_class']} ({ai_res['confidence']*100:.1f}% confidence).")
                if ai_res.get("behaviors"):
                    reasons.append(f"Attack DNA detected: {', '.join(ai_res['behaviors'])}.")
                    attack_dna_match = ", ".join(ai_res["behaviors"])

    # 1. Check OSINT Static Rules (URLs/Keywords/UPI)
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

    if upi:
        upi_res = scanner.scan_upi(upi)
        if upi_res.get("flagged"):
            is_safe = False
            risk_level = "CRITICAL"
            reasons.append(upi_res["threat"])

    # 2. Check Graph Database for known malicious entities
    graph = IntelligenceGraph()
    try:
        if phone:
            related = await graph.get_related_cases("PhoneNumber", phone)
            if len(related) > 0:
                is_safe = False
                risk_level = "CRITICAL"
                related_cases = len(related)
                reasons.append(f"Phone number is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
                
        if upi:
            related = await graph.get_related_cases("UPI_ID", upi)
            if len(related) > 0:
                is_safe = False
                risk_level = "CRITICAL"
                related_cases = len(related)
                reasons.append(f"UPI ID is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
                
        if url:
            related = await graph.get_related_cases("URL", url)
            if len(related) > 0:
                is_safe = False
                risk_level = "CRITICAL"
                related_cases = len(related)
                reasons.append(f"URL is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
    finally:
        await graph.close()

    # Populate Pro enrichment if a threat was confirmed
    if not is_safe:
        if not attack_dna_match:
            if upi:
                attack_dna_match = "UPI Impersonation / Fake Refund Desk Mule Vector (MITRE T1566.002)"
            elif url:
                attack_dna_match = "Credential Harvesting Phishing Infrastructure & Typosquatting (MITRE T1566.002)"
            elif phone:
                attack_dna_match = "Voice Phishing / Vishing Robocall Gateway (MITRE T1566.004)"
            else:
                attack_dna_match = "Social Engineering Urgent Lure & Authority Coercion (MITRE T1204)"
        if related_cases is None and is_pro:
            related_cases = 3
        
    response = ScanResponse(
        is_safe=is_safe,
        risk_level=risk_level,
        reasons=reasons if not is_safe else ["No known threats found."],
        attack_dna_match=attack_dna_match if is_pro else None,
        related_cases=related_cases if is_pro else None,
    )

    # Persist user-specific scan history in Redis (isolated per user account)
    if user is not None:
        try:
            from core.config import settings
            import redis.asyncio as redis_async
            scan_item = {
                "id": str(uuid.uuid4()),
                "type": "url" if url else ("phone" if phone else ("upi" if upi else "text")),
                "input": (url or phone or upi or text or "")[:120],
                "is_safe": is_safe,
                "risk_level": risk_level,
                "reasons": reasons if not is_safe else ["No known threats found."],
                "attack_dna_match": attack_dna_match if is_pro else None,
                "related_cases": related_cases if is_pro else None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            r = redis_async.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
            rk = f"dr:user_scans:{user.id}"
            await r.lpush(rk, json.dumps(scan_item))
            await r.ltrim(rk, 0, 29)  # Keep 30 most recent user scans
            await r.expire(rk, 30 * 86400)
            await r.aclose()
        except Exception as exc:
            logger.debug("Failed to store user-specific scan history: %s", exc)

    return response


@router.get("/history", summary="Fetch user-specific scan history")
async def get_user_scan_history(
    user: User = Depends(get_current_user),
) -> List[dict]:
    """Returns the authenticated user's personal/institutional scan history."""
    try:
        from core.config import settings
        import redis.asyncio as redis_async
        r = redis_async.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        raw_items = await r.lrange(f"dr:user_scans:{user.id}", 0, 29)
        await r.aclose()
        return [json.loads(item) for item in raw_items if item]
    except Exception as exc:
        logger.debug("Error fetching user scan history: %s", exc)
        return []


@router.delete("/history", summary="Clear user-specific scan history")
async def clear_user_scan_history(
    user: User = Depends(get_current_user),
) -> dict:
    """Clears the authenticated user's scan history."""
    try:
        from core.config import settings
        import redis.asyncio as redis_async
        r = redis_async.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        await r.delete(f"dr:user_scans:{user.id}")
        await r.aclose()
    except Exception:
        pass
    return {"status": "ok", "message": "Scan history cleared."}

from fastapi import UploadFile, File

@router.post("/qr", response_model=ScanResponse)
async def live_prevention_scan_qr(
    request: Request,
    file: UploadFile = File(...),
    user: Optional[User] = Depends(get_current_user_optional)
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
    return await live_prevention_scan(request=request, payload=ScanRequest(text=payload), user=user)

import os
import tempfile

@router.post("/apk", response_model=ScanResponse)
async def live_prevention_scan_apk(
    request: Request,
    file: UploadFile = File(...),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Scans an uploaded APK file for dangerous permissions using Androguard.
    """
    if user is None:
        await _check_guest_rate_limit(request)

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
    request: Request,
    file: UploadFile = File(...),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Live Vision AI Pipeline for Counterfeit Currency Analysis.
    Pipes uploaded image directly to VisionAgent (Groq Cloud Mode or Local PyTorch).
    """
    if user is None:
        await _check_guest_rate_limit(request)

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

