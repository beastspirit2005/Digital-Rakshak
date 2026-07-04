from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from infrastructure.db.session import get_db
from api.v1.users import get_current_user_token
from domain.models.case import Case, CaseStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db), user_payload: dict = Depends(get_current_user_token)):
    """
    Returns aggregated analytics for the National Intelligence Dashboard.
    """
    role = user_payload.get("role")
    if role not in ["admin", "police"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 1. High-level stats
    total_cases = await db.execute(select(func.count(Case.id)))
    total_cases_count = total_cases.scalar() or 0

    resolved_cases = await db.execute(select(func.count(Case.id)).where(Case.status == CaseStatus.RESOLVED.value))
    resolved_cases_count = resolved_cases.scalar() or 0
    
    high_priority = await db.execute(select(func.count(Case.id)).where(Case.priority == "High"))
    high_priority_count = high_priority.scalar() or 0

    # 2. Scam Types Breakdown
    scam_types_query = await db.execute(
        select(Case.scam_type_code, func.count(Case.id))
        .where(Case.scam_type_code.isnot(None))
        .group_by(Case.scam_type_code)
    )
    scam_types = [{"name": row[0], "value": row[1]} for row in scam_types_query.all()]

    # 3. State-wise breakdown
    state_query = await db.execute(
        select(Case.state, func.count(Case.id))
        .where(Case.state.isnot(None))
        .group_by(Case.state)
    )
    state_distribution = [{"state": row[0], "cases": row[1]} for row in state_query.all()]

    # 4. Mocked Timeline (last 7 days for the MVP)
    import datetime
    timeline = []
    today = datetime.datetime.now()
    for i in range(6, -1, -1):
        d = today - datetime.timedelta(days=i)
        # Mock some varied data for a nice chart based on the total case count
        # In production this would group by func.date(Case.created_at)
        timeline.append({
            "date": d.strftime("%b %d"),
            "reports": max(1, (total_cases_count // 7) + (i % 3)) 
        })

    return {
        "stats": {
            "total_cases": total_cases_count,
            "resolved_cases": resolved_cases_count,
            "high_priority": high_priority_count,
            "threat_level": "CRITICAL" if high_priority_count > (total_cases_count * 0.3) else "ELEVATED"
        },
        "scam_types": scam_types if scam_types else [{"name": "Phishing", "value": 1}],
        "state_distribution": state_distribution if state_distribution else [{"state": "Maharashtra", "cases": 1}],
        "timeline": timeline
    }
