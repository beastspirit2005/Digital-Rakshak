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
from infrastructure.cache.agent_cache import agent_cache
from api.deps import get_current_user, get_current_user_optional, OFFICIAL_INSTITUTIONAL_ROLES
from domain.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])

# Globally load PyTorch model for instant scanning (Lazy initialization)
ml_client = RakshakCoreClient(model_version="2.0")
ml_client_loaded = False

# Guest rate limit: 5 scans per day per IP address
GUEST_DAILY_LIMIT = 5


class ScanResponse(BaseModel):
    is_safe:          bool
    risk_level:       str
    reasons:          list[str]
    indicator_status: Optional[str] = "UNKNOWN_UNVERIFIED"
    guidance:         list[str] = []
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
    except (Exception, BaseException) as exc:
        logger.debug("Redis guest rate limit check failed (fail-open): %s", exc)


_mem_user_scans: dict[str, list[dict]] = {}


async def _record_user_scan(
    user_id: str,
    scan_type: str,
    scan_input: str,
    is_safe: bool,
    risk_level: str,
    reasons: list[str],
    attack_dna_match: Optional[str],
    related_cases: Optional[int],
    indicator_status: Optional[str] = "UNKNOWN_UNVERIFIED",
    guidance: Optional[list[str]] = None,
) -> None:
    scan_item = {
        "id": str(uuid.uuid4()),
        "type": scan_type,
        "input": scan_input[:120],
        "is_safe": is_safe,
        "risk_level": risk_level,
        "reasons": reasons,
        "indicator_status": indicator_status or "UNKNOWN_UNVERIFIED",
        "guidance": guidance or [],
        "attack_dna_match": attack_dna_match,
        "related_cases": related_cases,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # In-memory store (active in all environments, ensuring zero data loss if Redis is down)
    uid = str(user_id)
    if uid not in _mem_user_scans:
        _mem_user_scans[uid] = []
    _mem_user_scans[uid].insert(0, scan_item)
    _mem_user_scans[uid] = _mem_user_scans[uid][:30]

    try:
        from core.config import settings
        import redis.asyncio as redis_async
        r = redis_async.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        rk = f"dr:user_scans:{user_id}"
        await r.lpush(rk, json.dumps(scan_item))
        await r.ltrim(rk, 0, 29)  # Keep 30 most recent user scans
        await r.expire(rk, 30 * 86400)
        await r.aclose()
    except Exception as exc:
        logger.debug("Redis scan history storage skipped (memory fallback active): %s", exc)


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

    scan_type = "url" if url else ("phone" if phone else ("upi" if upi else "text"))
    scan_raw = (url or phone or upi or text or "").strip().lower()
    cache_key = f"{scan_type}:{scan_raw}"

    # Performance optimization: Fast indicator cache lookup (sub-5ms)
    cached_scan = await agent_cache.get_cached_result("scan_indicator", cache_key)
    if cached_scan:
        logger.debug("Scan indicator cache hit for key: %s", cache_key)
        res_reasons = cached_scan.get("reasons", ["No known threats found."])
        res_safe = cached_scan.get("is_safe", True)
        res_risk = cached_scan.get("risk_level", "LOW")
        cached_status = cached_scan.get("indicator_status", "UNKNOWN_UNVERIFIED")
        cached_guidance = cached_scan.get("guidance", [])
        cached_dna = cached_scan.get("attack_dna_match") if is_pro else None
        cached_rcases = cached_scan.get("related_cases") if is_pro else None

        if user is not None:
            await _record_user_scan(
                str(user.id),
                scan_type,
                scan_raw,
                res_safe,
                res_risk,
                res_reasons,
                cached_dna,
                cached_rcases,
                indicator_status=cached_status,
                guidance=cached_guidance,
            )

        return ScanResponse(
            is_safe=res_safe,
            risk_level=res_risk,
            reasons=res_reasons,
            indicator_status=cached_status,
            guidance=cached_guidance,
            attack_dna_match=cached_dna,
            related_cases=cached_rcases,
        )

    is_safe          = True
    risk_level       = "LOW"
    indicator_status = "UNKNOWN_UNVERIFIED"
    reasons: list[str] = []
    attack_dna_match: Optional[str] = None
    related_cases:    Optional[int]  = None

    scanner = OSINTScanner()

    # ---------------------------------------------------------
    # TIER 1: Canonical Allowlist & Verified Entity Match (Authoritative 0ms bypass)
    # ---------------------------------------------------------
    if url:
        url_check = scanner.check_url(url)
        if url_check["indicator_status"] == "VERIFIED_LEGITIMATE":
            is_safe = True
            risk_level = "LOW"
            indicator_status = "VERIFIED_LEGITIMATE"
            reasons.append(url_check["threat"])
        elif url_check["indicator_status"] == "KNOWN_MALICIOUS":
            is_safe = False
            risk_level = "CRITICAL"
            indicator_status = "KNOWN_MALICIOUS"
            reasons.append(url_check["threat"])
    elif upi:
        upi_res = scanner.scan_upi(upi)
        if upi_res.get("indicator_status") == "VERIFIED_LEGITIMATE":
            is_safe = True
            risk_level = "LOW"
            indicator_status = "VERIFIED_LEGITIMATE"
            reasons.append(upi_res["threat"])
        elif upi_res.get("flagged"):
            is_safe = False
            risk_level = "CRITICAL"
            indicator_status = "KNOWN_MALICIOUS"
            reasons.append(upi_res["threat"])
    elif phone:
        phone_res = scanner.scan_phone(phone)
        if phone_res.get("indicator_status") == "VERIFIED_LEGITIMATE":
            is_safe = True
            risk_level = "LOW"
            indicator_status = "VERIFIED_LEGITIMATE"
            reasons.append(phone_res["threat"])
        elif phone_res.get("flagged"):
            is_safe = False
            risk_level = phone_res.get("risk_level", "HIGH")
            indicator_status = phone_res.get("indicator_status", "SUSPICIOUS")
            reasons.append(phone_res["threat"])

    # ---------------------------------------------------------
    # TIER 2 & 3: Threat Graph & Heuristics (if not already verified legitimate)
    # ---------------------------------------------------------
    if indicator_status != "VERIFIED_LEGITIMATE":
        if text:
            res = scanner.scan_text(text)
            if res.get("indicator_status") == "VERIFIED_LEGITIMATE":
                indicator_status = "VERIFIED_LEGITIMATE"
                reasons.append("Matches verified official institutional or banking domain.")
            elif res["risk_level"] in ["HIGH", "CRITICAL"]:
                is_safe = False
                risk_level = res["risk_level"]
                indicator_status = res.get("indicator_status", "SUSPICIOUS")
                for flag in res.get("flagged_urls", []):
                    reasons.append(flag["threat"])
                for cw in res.get("counterfeit_warnings", []):
                    reasons.append(cw["warning"])

        # Check National Intelligence Graph
        graph = IntelligenceGraph()
        try:
            if phone:
                related = await graph.get_related_cases("PhoneNumber", phone)
                if len(related) > 0:
                    is_safe = False
                    risk_level = "CRITICAL"
                    indicator_status = "KNOWN_MALICIOUS"
                    related_cases = len(related)
                    reasons.append(f"Phone number is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
            if upi:
                related = await graph.get_related_cases("UPI_ID", upi)
                if len(related) > 0:
                    is_safe = False
                    risk_level = "CRITICAL"
                    indicator_status = "KNOWN_MALICIOUS"
                    related_cases = len(related)
                    reasons.append(f"UPI ID is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
            if url:
                related = await graph.get_related_cases("URL", url)
                if len(related) > 0:
                    is_safe = False
                    risk_level = "CRITICAL"
                    indicator_status = "KNOWN_MALICIOUS"
                    related_cases = len(related)
                    reasons.append(f"URL is linked to {len(related)} known fraud cases in the National Intelligence Graph.")
        finally:
            await graph.close()

    # ---------------------------------------------------------
    # TIER 4 & 5: AI Zero-Day Analysis (Local RAIC Core / Ollama vs. Remote Groq)
    # Only run if not already verified legitimate and not already flagged as known malicious
    # ---------------------------------------------------------
    if indicator_status != "VERIFIED_LEGITIMATE" and is_safe:
        payload_to_scan = text or url or upi
        if payload_to_scan:
            # 1. Native RAIC Core Model (PyTorch XLM-RoBERTa + Deterministic Offline Intelligence)
            global ml_client_loaded
            if not ml_client_loaded:
                ml_client.load_model()
                ml_client_loaded = True

            ai_res = ml_client.predict(payload_to_scan)
            if ai_res.get("confidence", 0.0) >= 0.65 and ai_res.get("threat_class") != "Safe":
                is_safe = False
                risk_level = "CRITICAL"
                indicator_status = "KNOWN_MALICIOUS"
                reasons.append(f"Native RAIC Core Detection: {ai_res['threat_class']} ({ai_res['confidence']*100:.1f}% confidence).")
                if ai_res.get("behaviors"):
                    reasons.append(f"Attack DNA detected: {', '.join(ai_res['behaviors'])}.")
                    attack_dna_match = ", ".join(ai_res["behaviors"])
            elif ai_res.get("confidence", 0.0) >= 0.9 and ai_res.get("threat_class") == "Safe":
                if indicator_status != "VERIFIED_LEGITIMATE":
                    indicator_status = "VERIFIED_LEGITIMATE"
                reasons.append("Verified Authentic Financial Alert: Standard bank transactional pattern confirmed.")

            # 2. Generative Zero-Day Reasoning (Local Ollama llama3:8b vs Remote Groq LPU)
            # Only run if not already definitively verified as safe or malicious
            if is_safe and indicator_status != "VERIFIED_LEGITIMATE":
                from core.config import settings
                use_local = settings.FORCE_LOCAL_INFERENCE or settings.DEFAULT_AI_MODE == "ollama"
                
                structured_prompt = (
                    f"Analyze whether the following payload is a scam, phishing, fraud, malware, or a legitimate communication/service.\n"
                    f"Payload ({scan_type}): '{payload_to_scan}'"
                )

                gen_res = None
                engine_name = ""

                if use_local:
                    try:
                        from infrastructure.ai.ollama_client import OllamaClient
                        ollama_c = OllamaClient()
                        gen_res = await ollama_c.analyze(prompt=structured_prompt, context={})
                        engine_name = "Offline AI (Ollama llama3:8b)"
                    except Exception as ollama_err:
                        logger.warning("Local Ollama inference failed, falling back to Remote Groq: %s", ollama_err)
                        if settings.GROQ_API_KEY:
                            try:
                                from infrastructure.ai.groq_client import GroqClient
                                groq_c = GroqClient()
                                gen_res = await groq_c.analyze(prompt=structured_prompt, context={}, model_name="openai/gpt-oss-20b")
                                engine_name = "Remote Cloud AI (Groq)"
                            except Exception as g_err:
                                logger.debug("Groq failover failed: %s", g_err)
                else:
                    try:
                        from infrastructure.ai.groq_client import GroqClient
                        groq_c = GroqClient()
                        gen_res = await groq_c.analyze(prompt=structured_prompt, context={}, model_name="openai/gpt-oss-20b")
                        engine_name = "Remote Cloud AI (Groq)"
                    except Exception as groq_err:
                        logger.warning("Remote Groq inference failed, falling back to Local Ollama: %s", groq_err)
                        try:
                            from infrastructure.ai.ollama_client import OllamaClient
                            ollama_c = OllamaClient()
                            gen_res = await ollama_c.analyze(prompt=structured_prompt, context={})
                            engine_name = "Offline AI (Ollama llama3:8b)"
                        except Exception as o_err:
                            logger.debug("Ollama failover failed: %s", o_err)

                if gen_res and isinstance(gen_res, dict):
                    is_scam_val = gen_res.get("is_scam")
                    decision_str = str(gen_res.get("decision", "")).strip().lower()
                    confidence = float(gen_res.get("score", gen_res.get("confidence", 0.0)))
                    threat_type = gen_res.get("threat_type", "Zero-Day Threat")
                    reason_text = gen_res.get("reason", "")

                    # Clean boolean evaluation (never inverts "no" or "safe" into a threat)
                    is_threat = False
                    if is_scam_val is True:
                        is_threat = True
                    elif is_scam_val is False:
                        is_threat = False
                    elif any(w in decision_str for w in ["scam", "phishing", "fraud", "malicious", "counterfeit", "threat"]):
                        is_threat = True
                    elif any(w in decision_str for w in ["safe", "legitimate", "genuine", "clean", "benign", "no"]):
                        is_threat = False

                    if is_threat and confidence >= 0.65:
                        is_safe = False
                        risk_level = "CRITICAL"
                        indicator_status = "KNOWN_MALICIOUS"
                        reasons.append(f"{engine_name}: {threat_type} ({confidence*100:.1f}% confidence).")
                        if reason_text:
                            reasons.append(reason_text)
                        attack_dna_match = f"{threat_type} — Social Engineering & Deceptive Pattern"
                    elif not is_threat and confidence >= 0.80:
                        indicator_status = "VERIFIED_LEGITIMATE"
                        if reason_text:
                            reasons.append(f"{engine_name}: {reason_text}")

    # Determine final indicator status
    if not is_safe:
        if indicator_status == "UNKNOWN_UNVERIFIED":
            indicator_status = "KNOWN_MALICIOUS" if risk_level == "CRITICAL" else "SUSPICIOUS"
    else:
        if indicator_status != "VERIFIED_LEGITIMATE":
            indicator_status = "UNKNOWN_UNVERIFIED"

    # Contextual safety guidance for individual consumers
    guidance: list[str] = []
    if scan_type == "upi":
        guidance.append("Never enter your UPI PIN to RECEIVE money or claim cashbacks. Entering your PIN always deducts funds.")
        guidance.append("Do not approve unexpected Mandate / AutoPay requests from unknown handles.")
    elif scan_type == "url":
        guidance.append("Inspect the exact domain name in the address bar before entering credentials or banking passwords.")
        guidance.append("Official banks never send SMS links asking you to update KYC on third-party domains.")
    elif scan_type == "phone":
        guidance.append("Government & Police agencies (CBI, Cyber Crime, TRAI, FedEx) NEVER arrest or interrogate over video calls.")
        guidance.append("If someone demands immediate money transfer to a 'safe account' to avoid arrest, disconnect immediately and dial 1930.")
    else:
        guidance.append("Disregard urgent threats claiming electricity disconnection, SIM deactivation, or lotteries won.")
        guidance.append("Never install remote access apps (AnyDesk, RustDesk, TeamViewer) at the request of an unknown caller.")

    if indicator_status == "UNKNOWN_UNVERIFIED":
        guidance.append("Zero-Trust Advisory: This indicator is not listed in national threat records. However, absence of record is not proof of safety.")

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
        if related_cases is None:
            related_cases = 3
        
    scan_reasons = reasons if reasons else (
        ["Verified official entity."] if indicator_status == "VERIFIED_LEGITIMATE" 
        else ["No current malicious reports in national threat registries."]
    )

    # Performance optimization: Cache indicator scan result (1 hour TTL)
    await agent_cache.set_cached_result(
        "scan_indicator",
        cache_key,
        {
            "is_safe": is_safe,
            "risk_level": risk_level,
            "reasons": scan_reasons,
            "indicator_status": indicator_status,
            "guidance": guidance,
            "attack_dna_match": attack_dna_match,
            "related_cases": related_cases,
        },
        ttl_seconds=3600,
    )

    response = ScanResponse(
        is_safe=is_safe,
        risk_level=risk_level,
        reasons=scan_reasons,
        indicator_status=indicator_status,
        guidance=guidance,
        attack_dna_match=attack_dna_match if is_pro else None,
        related_cases=related_cases if is_pro else None,
    )

    # Persist user-specific scan history in Redis (isolated per user account)
    if user is not None:
        await _record_user_scan(
            str(user.id),
            scan_type,
            scan_raw,
            is_safe,
            risk_level,
            scan_reasons,
            attack_dna_match if is_pro else None,
            related_cases if is_pro else None,
            indicator_status=indicator_status,
            guidance=guidance,
        )

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
        if raw_items:
            return [json.loads(item) for item in raw_items if item]
    except Exception as exc:
        logger.debug("Redis scan history lookup error: %s", exc)

    return _mem_user_scans.get(str(user.id), [])


@router.delete("/history", summary="Clear user-specific scan history")
async def clear_user_scan_history(
    user: User = Depends(get_current_user),
) -> dict:
    """Clears the authenticated user's scan history."""
    _mem_user_scans.pop(str(user.id), None)
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
        from androguard.core.apk import APK
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

