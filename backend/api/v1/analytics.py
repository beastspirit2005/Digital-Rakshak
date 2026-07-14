from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from infrastructure.db.session import get_db
from api.deps import get_current_user, get_current_admin
from domain.models.user import User
from domain.models.case import Case, CaseStatus
from infrastructure.graph.neo4j_client import IntelligenceGraph

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns aggregated analytics for the National Intelligence Dashboard.
    """
    role = user.role
    print(f"DEBUG: analytics user.role is {repr(role)}")
    if role not in ["admin", "police", "cyber_cell"]:
        print(f"DEBUG: raising 403 in analytics because {repr(role)} not in allowed list")
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 1. High-level stats
    total_cases = await db.execute(select(func.count(Case.id)))
    total_cases_count = total_cases.scalar() or 0

    resolved_cases = await db.execute(select(func.count(Case.id)).where(Case.status == CaseStatus.resolved.value))
    resolved_cases_count = resolved_cases.scalar() or 0
    
    from domain.models.case import CasePriority
    high_priority = await db.execute(select(func.count(Case.id)).where(Case.priority == CasePriority.high.value))
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

    # 4. Actual Timeline from DB
    result = await db.execute(
        select(cast(Case.created_at, Date), func.count(Case.id))
        .group_by(cast(Case.created_at, Date))
        .order_by(cast(Case.created_at, Date).desc())
        .limit(7)
    )
    
    timeline_rows = result.all()
    # Reverse to show chronological order
    timeline = [{"date": row[0].strftime("%b %d") if row[0] else "Unknown", "reports": row[1]} for row in reversed(timeline_rows)]
    
    # Fallback if DB has no cases yet
    if not timeline:
        import datetime
        timeline = [{"date": datetime.datetime.now().strftime("%b %d"), "reports": 0}]

    # 5. Graph Intelligence (Neo4j)
    graph = IntelligenceGraph()
    try:
        clusters = await graph.get_connected_clusters()
        clusters_count = len(clusters)
    except Exception:
        clusters_count = 0
    finally:
        await graph.close()

    return {
        "stats": {
            "total_cases": total_cases_count,
            "resolved_cases": resolved_cases_count,
            "high_priority": high_priority_count,
            "threat_level": "CRITICAL" if high_priority_count > (total_cases_count * 0.3) else "ELEVATED",
            "scam_clusters": clusters_count
        },
        "scam_types": scam_types if scam_types else [{"name": "Phishing", "value": 1}],
        "state_distribution": state_distribution if state_distribution else [{"state": "Maharashtra", "cases": 1}],
        "timeline": timeline
    }
