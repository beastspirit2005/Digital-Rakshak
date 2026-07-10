from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from sqlalchemy import select
import os
import shutil
import uuid

from infrastructure.db.session import get_db
from domain.models.case import Case, CaseStatus
from domain.agents.threat_agent import ThreatAnalysisAgent
from api.deps import get_current_user, get_current_admin
from domain.models.user import User
from core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# Model removed, now using Form fields directly for multipart/form-data



@router.get("/")
@router.get("")
@limiter.limit("60/minute")
async def get_cases(request: Request, db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 50, user: User = Depends(get_current_user)):
    """
    Returns cases based on role. Citizens see none (they should use /my).
    Police/Admin see all.
    """
    role = user.role
    if role not in ["admin", "police"]:
        raise HTTPException(status_code=403, detail="Citizens must use /my endpoint")
        
    from sqlalchemy import desc
    result = await db.execute(select(Case).order_by(desc(Case.created_at)).offset(skip).limit(limit))
    cases = result.scalars().all()
    return {"cases": cases}

@router.get("/my")
@limiter.limit("60/minute")
async def get_my_cases(request: Request, db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 50, user: User = Depends(get_current_user)):
    """
    Returns cases created by the current citizen.
    """
    user_id = str(user.id)
    from sqlalchemy import desc
    result = await db.execute(select(Case).where(Case.submitted_by == user_id).order_by(desc(Case.created_at)).offset(skip).limit(limit))
    cases = result.scalars().all()
    return {"cases": cases}

from fastapi import BackgroundTasks
import urllib.request
import json

@router.get("/location")
async def get_location(lat: float, lon: float):
    """
    Proxies the reverse geocoding request to BigDataCloud to bypass frontend ad-blockers.
    """
    try:
        url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return {
                "city": data.get("city") or data.get("locality") or "",
                "state": data.get("principalSubdivision") or data.get("countryName") or ""
            }
    except Exception as e:
        print(f"Backend geocoding failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch location data")

@router.post("/submit")
@limiter.limit("5/minute")
async def submit_case(
    request: Request,
    background_tasks: BackgroundTasks,
    scam_text: str = Form(...),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    ai_mode: str = Form("auto"),
    report_type: str = Form("scam"),
    file: Optional[UploadFile] = File(None),
    victim_phone: Optional[str] = Form(None),
    victim_address: Optional[str] = Form(None),
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    """
    Accepts raw scam text and optional file, triggers the ThreatAnalysisAgent, and saves the result.
    """
    user_id = str(user.id)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
        

    
    # 1. Save the Case to PostgreSQL FIRST (Save First, Analyze Second)
    new_case = Case(
        case_number=f"CAS-{uuid.uuid4().hex[:8].upper()}",
        submitted_by=str(user.id),
        scam_text=scam_text,
        city=city,
        state=state,
        latitude=latitude,
        longitude=longitude,
        threat_confidence_score=0.0,
        ai_decision={},
        status=CaseStatus.submitted.value,
        victim_phone=victim_phone,
        victim_address=victim_address
    )
    file_bytes = None
    file_path = None
    ev_type = None
    if file:
        file_bytes = await file.read()
        if len(file_bytes) > 50 * 1024 * 1024:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Evidence file too large. Maximum allowed size is 50MB.")
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf", ".apk"}
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, PDF, and APK are allowed.")

    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    
    # 1.5 Save uploaded file if any
    if file and file_bytes:
        upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf", ".apk"}
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, PDF, and APK are allowed.")
            
        safe_filename = f"{new_case.case_number}_{uuid.uuid4().hex[:6]}{file_ext}"
        
        # Hybrid Storage Strategy
        from core.config import settings
        import hashlib
        
        file_hash = hashlib.sha256()
        file_hash.update(file_bytes)
        sha256_digest = file_hash.hexdigest()
        
        is_cloud_storage = bool(settings.SUPABASE_URL and settings.SUPABASE_KEY)
        file_path_in_db = ""
        local_tmp_path = os.path.join(upload_dir, f"tmp_{safe_filename}")
        
        # Write temporary decrypted file for AI analysis
        with open(local_tmp_path, "wb") as f:
            f.write(file_bytes)
        file_path = local_tmp_path
        
        if is_cloud_storage:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            
            # Ensure bucket exists or create it
            try:
                supabase.storage.get_bucket("evidence")
            except Exception:
                try:
                    supabase.storage.create_bucket("evidence", options={"public": False})
                except Exception:
                    pass # Ignore if it already exists or creation fails
            
            try:
                supabase.storage.from_("evidence").upload(
                    path=safe_filename,
                    file=file_bytes,
                    file_options={"content-type": file.content_type or "application/octet-stream"}
                )
                file_path_in_db = f"supabase://evidence/{safe_filename}"
            except Exception as e:
                print(f"Supabase upload failed (likely RLS policy missing): {e}. Falling back to local storage.")
                is_cloud_storage = False  # Trigger fallback
        
        if not is_cloud_storage:
            from cryptography.fernet import Fernet
            import base64
            
            raw_key = settings.LOCAL_FILE_ENCRYPTION_KEY
            if not raw_key:
                # Generate a secure 32-byte key dynamically instead of falling back to insecure hardcoded string
                raw_key = Fernet.generate_key().decode('utf-8')
                print("WARNING: LOCAL_FILE_ENCRYPTION_KEY not found in env. Generated ephemeral key for session.")
                
            key = raw_key if raw_key.endswith('=') else raw_key + '=' * (4 - len(raw_key) % 4)
            fernet = Fernet(key.encode())
            
            encrypted_data = fernet.encrypt(file_bytes)
            final_file_path = os.path.join(upload_dir, safe_filename)
            with open(final_file_path, "wb") as buffer:
                buffer.write(encrypted_data)
                
            file_path_in_db = f"local://{safe_filename}"
            
        from domain.models.evidence import Evidence, EvidenceType
        
        ev_type = EvidenceType.RAW_TEXT.value
        if file_ext.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
            ev_type = EvidenceType.SCREENSHOT.value
        elif file_ext.lower() in [".pdf"]:
            ev_type = EvidenceType.PDF.value
        elif file_ext.lower() in [".apk"]:
            ev_type = EvidenceType.APK.value
        elif file_ext.lower() in [".mp3", ".wav", ".m4a"]:
            ev_type = EvidenceType.AUDIO.value
            
        new_evidence = Evidence(
            case_id=new_case.id,
            evidence_type=ev_type,
            file_path=file_path_in_db,
            source="citizen_upload",
        )
        setattr(new_evidence, 'file_hash_sha256', sha256_digest)
        
        db.add(new_evidence)
        await db.commit()
        
        # Phase 1: Malicious APK Scanner Integration
        if ev_type == EvidenceType.APK.value:
            from infrastructure.osint.apk_scanner import APKScanner
            apk_scanner = APKScanner()
            apk_report = apk_scanner.scan_apk(file_path)
            
            # Inject APK malware metadata into the scam text so the AI can analyze the fused threat
            scam_text += f"\n\n[SYSTEM MALWARE SCAN]: Uploaded APK '{apk_report['app_name']}' ({apk_report['package_name']}). "
            if apk_report['is_malicious']:
                scam_text += "WARNING: This APK requests highly dangerous permissions typical of banking trojans: "
                for flag in apk_report['flagged_permissions']:
                    scam_text += f"{flag['permission']} ({flag['threat']}), "
            else:
                scam_text += "No known critical malware permissions detected."
    
    # 2. Process AI synchronously (Vercel Serverless freezes BackgroundTasks)
    ai_decision = await process_case_background(
        case_number=new_case.case_number,
        scam_text=scam_text,
        ai_mode=ai_mode,
        report_type=report_type,
        file_path=file_path if file else None,
        ev_type=ev_type if file else None,
        city=city,
        latitude=latitude,
        longitude=longitude
    )
    if not ai_decision:
        ai_decision = {}
    
    # Send confirmation emails
    try:
        from domain.models.user import User
        from infrastructure.smtp.email_service import send_case_confirmation_email, send_admin_case_notification_email
        import asyncio
        from core.config import settings
        
        user_id = str(user.id)
        if user_id:
            res = await db.execute(select(User).where(User.id == user_id))
            user = res.scalar_one_or_none()
            
            threat_level = ai_decision.get('threat_class', 'Unknown')
            
            if user and user.email:
                # Notify citizen
                asyncio.create_task(send_case_confirmation_email(user.email, new_case.case_number, ai_decision))
                
            # Notify Admin
            if settings.ADMIN_EMAIL:
                asyncio.create_task(send_admin_case_notification_email(settings.ADMIN_EMAIL, new_case.case_number, threat_level))
                
    except Exception as e:
        print(f"Failed to send confirmation emails: {e}")
        
    # Clean up temporary decrypted file
    if file and 'file_path' in locals() and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
    
    return {
        "message": "Case submitted successfully and analyzed by AI",
        "case_number": new_case.case_number,
        "ai_analysis": ai_decision
    }

@router.get("/spatial")
async def get_spatial_cases(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns all cases with coordinates as a GeoJSON FeatureCollection.
    """
    # Security: Strict access control to prevent data scraping
    # For Hackathon: Allow all authenticated users to see the spatial map
    role = user.role
        
    # Fetch ALL cases to prevent dropping unknown locations
    result = await db.execute(select(Case))
    cases = result.scalars().all()
    
    import random
    
    features = []
    for case in cases:
        # Default to a central coordinate (e.g., Central India) if unknown
        lat = case.latitude if case.latitude is not None else 21.1458
        lng = case.longitude if case.longitude is not None else 79.0882
        is_unknown = case.latitude is None
        
        # Privacy Jitter / Stack Prevention
        if not is_unknown:
            lat += random.uniform(-0.005, 0.005) # ~500m noise
            lng += random.uniform(-0.005, 0.005)
        else:
            lat += random.uniform(-1.5, 1.5) # Wide spread for unassigned cases
            lng += random.uniform(-1.5, 1.5)
            
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat]
            },
            "properties": {
                "case_id": case.id,
                "case_number": case.case_number,
                "type": case.scam_type_code or "Unknown",
                "status": case.status,
                "priority": case.priority,
                "confidence_score": case.threat_confidence_score,
                "city": case.city,
                "state": case.state,
                "is_unknown_location": is_unknown
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

@router.get("/clusters")
async def get_spatial_clusters(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns GeoJSON LineStrings for cases connected in the Neo4j graph.
    """
    role = user.role
        
    from infrastructure.graph.neo4j_client import IntelligenceGraph
    graph = IntelligenceGraph()
    clusters = await graph.get_connected_clusters()
    await graph.close()
    
    features = []
    
    for cluster in clusters:
        case_ids = cluster["case_ids"] # These are case.case_number strings actually, wait no, neo4j c.id is case.case_number
        
        # Fetch the Postgres records for these cases to get coordinates
        # Neo4j query used c.id, which we set to case_number in add_case_entity_link
        result = await db.execute(select(Case).where(Case.case_number.in_(case_ids)).where(Case.latitude.isnot(None)))
        db_cases = result.scalars().all()
        
        if len(db_cases) < 2:
            continue
            
        coords = [[c.longitude, c.latitude] for c in db_cases]
        
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "entity_type": cluster["entity_type"],
                "entity_value": cluster["entity_value"],
                "case_numbers": [c.case_number for c in db_cases],
                "case_texts": [c.scam_text for c in db_cases] # Used by frontend to trigger summarization
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

from pydantic import BaseModel
class ClusterSummaryRequest(BaseModel):
    case_texts: list[str]

@router.post("/cluster/summary")
@limiter.limit("3/minute")
async def summarize_cluster(request: Request, req: ClusterSummaryRequest, user: User = Depends(get_current_user)):
    """Generates an AI summary for a cluster using Ollama."""
    from domain.agents.cluster_agent import ClusterAgent
    agent = ClusterAgent()
    # Mock format expected by agent
    mock_cases = [{"text": text} for text in req.case_texts]
    result = await agent.execute(mock_cases)
    return result

@router.post("/{case_id}/verify")
async def verify_case(case_id: int, correction: str = Form(...), db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    RLHF Continuous Learning: Save human corrections to the pgvector database.
    """
    from infrastructure.db.knowledge import MistakeCorrection, KnowledgeBase
    import json
    
    # Verify Admin/Official
    if user.role not in ["admin", "police"]:
        raise HTTPException(403, "Only officials can correct the AI.")
        
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Case not found")
        
    kb = KnowledgeBase()
    embedding = await kb.get_embedding(case.scam_text)
    
    if embedding:
        mistake = MistakeCorrection(
            original_scam_text=case.scam_text,
            ai_original_decision=json.dumps(case.ai_decision),
            human_correction=correction,
            embedding=embedding
        )
        db.add(mistake)
        
        # Confidence Evolution Engine:
        # Since an official verified this, we dynamically evolve the score to 99%
        # and lock the status as VERIFIED.
        case.threat_confidence_score = 0.99
        case.status = CaseStatus.verified.value if hasattr(CaseStatus, 'VERIFIED') else "verified"
        if isinstance(case.ai_decision, dict):
            case.ai_decision["confidence"] = 0.99
            case.ai_decision["decision"] = f"[OFFICIAL VERIFIED] {case.ai_decision.get('decision', '')}"
            
        await db.commit()
        
    return {"message": "Correction logged and Confidence Evolved to 99%."}

@router.post("/simulate-attack")
async def simulate_attack(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    HACKATHON FEATURE: Live Attack Simulator.
    Injects 15 interconnected cases in Mumbai to demonstrate the CTI graph and spatial map.
    """
    if user.role != "admin":
        raise HTTPException(403, "Only admins can simulate attacks.")
        
    import random
    
    # 3 bad actors to form clusters
    bad_phones = ["+919876543210", "+919998887776", "+915554443332"]
    
    # Base coordinates for Mumbai
    base_lat = 19.0760
    base_lon = 72.8777
    
    try:
        from infrastructure.graph.neo4j_client import IntelligenceGraph
        graph = IntelligenceGraph()
        
        for i in range(15):
            phone = random.choice(bad_phones)
            
            # Scatter coordinates slightly around Mumbai
            lat = base_lat + (random.uniform(-0.05, 0.05))
            lon = base_lon + (random.uniform(-0.05, 0.05))
            
            case_number = f"CAS-SIM-{uuid.uuid4().hex[:6].upper()}"
            
            new_case = Case(
                case_number=case_number,
                submitted_by=str(user.id),
                scam_text=f"I received a call from {phone} claiming my FedEx package was seized by customs. They asked for money.",
                city="Mumbai",
                state="Maharashtra",
                latitude=lat,
                longitude=lon,
                threat_confidence_score=0.95 + random.uniform(0.01, 0.04),
                ai_decision={
                    "decision": "Critical",
                    "confidence": 0.98,
                    "phone_numbers": [phone],
                    "urls": [],
                    "scam_type_code": "FEDEX_CUSTOMS_SCAM"
                },
                status=CaseStatus.under_review.value,
                priority="critical"
            )
            db.add(new_case)
            
            # Connect in Graph
            await graph.add_case_entity_link(case_number, "PhoneNumber", phone)
            
        await db.commit()
        await graph.close()
        
        return {"message": "Simulated attack successfully injected 15 cases into the database and graph."}
    except Exception as e:
        raise HTTPException(500, f"Simulation failed: {str(e)}")

@router.get("/{case_number}")
async def get_case(
    case_number: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a single case by case number.
    Admins/officials can fetch any case. Citizens can only fetch their own.
    """
    from sqlalchemy import select
    from domain.models.case import Case
    
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    role = user.role
    user_id = str(user.id)
    
    if role == "citizen" and str(case.submitted_by) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this case")
        
    return case

from fastapi.responses import StreamingResponse
import io

@router.get("/{case_number}/evidence")
async def get_case_evidence(
    case_number: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the evidence file securely. If Supabase, returns a signed URL.
    If Local, decrypts the file in-memory and streams it.
    """
    from domain.models.case import Case
    from domain.models.evidence import Evidence
    
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    role = user.role
    user_id = str(user.id)
    
    if role == "citizen" and str(case.submitted_by) != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this case")
        
    result = await db.execute(select(Evidence).where(Evidence.case_id == case.id))
    evidence = result.scalar_one_or_none()
    
    if not evidence or not evidence.file_path:
        raise HTTPException(status_code=404, detail="No evidence attached to this case")
        
    from core.config import settings
    path = evidence.file_path
    
    if path.startswith("supabase://"):
        bucket, filename = path.replace("supabase://", "").split("/", 1)
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        # Create a signed URL valid for 60 seconds
        res = supabase.storage.from_(bucket).create_signed_url(filename, 60)
        return {"url": res.get("signedURL", "")}
        
    elif path.startswith("local://"):
        filename = path.replace("local://", "")
        file_path = os.path.join(os.getcwd(), "uploads", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")
            
        from cryptography.fernet import Fernet
        import base64
        
        raw_key = settings.LOCAL_FILE_ENCRYPTION_KEY
        if not raw_key:
            raise HTTPException(status_code=500, detail="Server misconfiguration: LOCAL_FILE_ENCRYPTION_KEY is missing, cannot decrypt local evidence.")
            
        key = raw_key if raw_key.endswith('=') else raw_key + '=' * (4 - len(raw_key) % 4)
        fernet = Fernet(key.encode())
        
        with open(file_path, "rb") as buffer:
            encrypted_data = buffer.read()
            
        try:
            decrypted_data = fernet.decrypt(encrypted_data)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to decrypt evidence")
            
        file_ext = os.path.splitext(filename)[1].lower()
        content_type = "application/octet-stream"
        if file_ext in [".jpg", ".jpeg"]: content_type = "image/jpeg"
        elif file_ext == ".png": content_type = "image/png"
        elif file_ext == ".pdf": content_type = "application/pdf"
        
        return StreamingResponse(io.BytesIO(decrypted_data), media_type=content_type)
        
    raise HTTPException(status_code=400, detail="Invalid evidence storage format")

@router.post("/{case_number}/assign")
async def assign_case(
    case_number: str,
    investigator_id: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin assigns case to an investigator."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can assign cases")
        
    from domain.models.user import User
    
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    inv_result = await db.execute(select(User).where(User.id == investigator_id))
    investigator = inv_result.scalar_one_or_none()
    
    if not investigator or investigator.role not in ["police", "cyber_cell"]:
        raise HTTPException(status_code=400, detail="Invalid investigator ID")
        
    case.status = CaseStatus.assigned.value
    case.assigned_phone = investigator.station_phone_number
    
    await db.commit()
    
    from infrastructure.smtp.email_service import send_case_assigned_victim_email, send_case_assigned_investigator_email
    import asyncio
    
    # Fire off emails in background if email is available (mocking victim email logic)
    # Ideally, we fetch the submitter's email and send it.
    if case.submitted_by:
        submitter_res = await db.execute(select(User).where(User.id == case.submitted_by))
        submitter = submitter_res.scalar_one_or_none()
        if submitter and submitter.email:
            asyncio.create_task(send_case_assigned_victim_email(submitter.email, case.case_number))
            
    if investigator.email:
        asyncio.create_task(send_case_assigned_investigator_email(investigator.email, case.case_number))
    
    return {"message": f"Case {case_number} assigned to {investigator.full_name}"}

@router.post("/{case_number}/accept")
async def accept_case(
    case_number: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Investigator accepts an assigned case."""
    if user.role not in ["police", "cyber_cell"]:
        raise HTTPException(status_code=403, detail="Only investigators can accept cases")
        
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalar_one_or_none()
    
    if not case or case.status != CaseStatus.assigned.value:
        raise HTTPException(status_code=404, detail="Case not found or not in ASSIGNED status")
        
    case.status = CaseStatus.investigating.value
    await db.commit()
    
    from infrastructure.smtp.email_service import send_case_accepted_admin_email
    from core.config import settings
    import asyncio
    from domain.models.user import User
    
    # Send email to Admin
    if settings.ADMIN_EMAIL:
        investigator_res = await db.execute(select(User).where(User.id == str(user.id)))
        investigator = investigator_res.scalar_one_or_none()
        inv_name = investigator.full_name if investigator else "Unknown"
        asyncio.create_task(send_case_accepted_admin_email(settings.ADMIN_EMAIL, case.case_number, inv_name))
    
    return {"message": f"Case {case_number} accepted and is now INVESTIGATING"}

@router.post("/{case_number}/resolve")
async def resolve_case(
    case_number: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Citizen marks a case as resolved."""
    if user.role != "citizen":
        raise HTTPException(status_code=403, detail="Only the victim can resolve their case")
        
    result = await db.execute(select(Case).where(Case.case_number == case_number))
    case = result.scalar_one_or_none()
    
    if not case or str(case.submitted_by) != str(user.id):
        raise HTTPException(status_code=404, detail="Case not found or not yours")
        
    case.status = CaseStatus.resolved.value
    await db.commit()
    
    return {"message": f"Case {case_number} marked as RESOLVED"}

async def process_case_background(
    case_number: str,
    scam_text: str,
    ai_mode: str,
    report_type: str,
    file_path: Optional[str],
    ev_type: Optional[str],
    city: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float]
):
    from infrastructure.db.session import AsyncSessionLocal
    from domain.models.case import Case
    from sqlalchemy import select
    import asyncio
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Case).where(Case.case_number == case_number))
        case = result.scalar_one_or_none()
        if not case:
            return

        try:
            # Phase 1: Media Extraction
            processed_text = scam_text
            if file_path:
                from domain.models.evidence import EvidenceType
                if ev_type == EvidenceType.AUDIO.value:
                    from domain.agents.whisper_agent import WhisperAgent
                    audio_res = await WhisperAgent().execute({"text": file_path}, case.case_number)
                    processed_text += " " + " ".join(audio_res.get("evidence", []))
                elif ev_type == EvidenceType.SCREENSHOT.value:
                    from domain.agents.vision_agent import VisionAgent
                    vision_res = await VisionAgent().execute({"text": file_path}, case.case_number)
                    processed_text += " " + " ".join(vision_res.get("evidence", []))

            # Phase 2: Parallel Specialized Execution or Counterfeit Bypass
            if report_type == "counterfeit" and file_path:
                from domain.agents.vision_agent import VisionAgent
                payload = {"text": file_path, "ai_mode": ai_mode, "analyze_type": "counterfeit"}
                fused_decision = await VisionAgent().execute(payload, case.case_number)
                
                # Mock fusion structure for UI
                if "threat_class" not in fused_decision:
                    fused_decision["threat_class"] = "Counterfeit Note"
                fused_decision["raw_explanation"] = fused_decision.get("decision", "Counterfeit currency analysis.")
                
            else:
                payload = {"text": processed_text, "ai_mode": ai_mode}
                
                from domain.agents.threat_agent import ThreatAnalysisAgent
                from domain.agents.behaviour_agent import BehaviourAgent
                from domain.agents.campaign_agent import CampaignAgent
                from domain.agents.trust_validation_agent import TrustValidationAgent
                
                t_task = asyncio.create_task(ThreatAnalysisAgent().execute(payload, case.case_number))
                b_task = asyncio.create_task(BehaviourAgent().execute(payload, case.case_number))
                c_task = asyncio.create_task(CampaignAgent().execute(payload, case.case_number))
                tr_task = asyncio.create_task(TrustValidationAgent().execute(payload, case.case_number))
                
                t_res, b_res, c_res, tr_res = await asyncio.gather(t_task, b_task, c_task, tr_task)
                
                # Phase 3: RAIC Decision Core Fusion
                from domain.agents.router import RAICDecisionCore
                core = RAICDecisionCore()
                fused_decision = await core.execute_fusion([t_res, b_res, c_res, tr_res], use_qwen_refinement=True, ai_mode=ai_mode)
            
            
            # Update Case Record locally in memory for now
            case.threat_confidence_score = fused_decision.get("confidence", 0.0)
            case.ai_decision = fused_decision
            case.status = CaseStatus.under_review.value
            
            # Coordinates
            CITY_COORDINATES = {
                "mumbai": {"lat": 19.0760, "lng": 72.8777},
                "delhi": {"lat": 28.7041, "lng": 77.1025},
                "bengaluru": {"lat": 12.9716, "lng": 77.5946},
                "bangalore": {"lat": 12.9716, "lng": 77.5946}
            }
            if latitude is not None and longitude is not None:
                case.latitude = latitude
                case.longitude = longitude
            elif city and city.lower().strip() in CITY_COORDINATES:
                case.latitude = CITY_COORDINATES[city.lower().strip()]["lat"]
                case.longitude = CITY_COORDINATES[city.lower().strip()]["lng"]
            
            await db.commit()
            
            # Phase 4: Data Persistence via IntelligenceAgent
            from domain.agents.intelligence_agent import IntelligenceAgent
            intelligence_payload = {
                "decision": fused_decision,
                "case_number": case.case_number,
                "entities": c_res.get("entities", {})
            }
            await IntelligenceAgent().execute(intelligence_payload, case.case_number)
            return fused_decision
            
        except Exception as e:
            print(f"MAIF Orchestrator failed: {e}. Executing Regex Fallback...")
            import re
            phones = list(set(re.findall(r'\+?\d{10,13}', scam_text)))
            ai_decision = {
                "decision": "Manual Review Required (AI Offline).",
                "score": 0.5,
                "phone_numbers": phones,
                "error_trace": str(e)[:200]
            }
            case.threat_confidence_score = 0.5
            case.ai_decision = ai_decision
            case.status = CaseStatus.under_review.value
            await db.commit()
            return ai_decision
