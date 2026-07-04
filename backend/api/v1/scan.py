from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from infrastructure.osint.scanner import OSINTScanner
from infrastructure.graph.neo4j_client import IntelligenceGraph
from pydantic import BaseModel

router = APIRouter(prefix="/scan", tags=["scan"])

class ScanResponse(BaseModel):
    is_safe: bool
    risk_level: str
    reasons: list[str]

@router.get("", response_model=ScanResponse)
async def live_prevention_scan(
    url: Optional[str] = None, 
    phone: Optional[str] = None,
    upi: Optional[str] = None
):
    """
    Live Prevention Shield API.
    Used by browser extensions, mobile apps, or citizens to instantly check if an entity is safe.
    """
    if not any([url, phone, upi]):
        raise HTTPException(status_code=400, detail="Must provide at least one parameter to scan (url, phone, or upi).")
        
    is_safe = True
    risk_level = "LOW"
    reasons = []
    
    # 1. Check OSINT Static Rules (URLs/Keywords)
    scanner = OSINTScanner()
    if url:
        res = scanner.scan_text(url)
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
