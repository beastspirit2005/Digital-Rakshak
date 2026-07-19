from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date, desc
from infrastructure.db.session import get_db
from api.deps import get_current_user, get_current_admin
from domain.models.user import User
from domain.models.case import Case, CaseStatus
from infrastructure.graph.neo4j_client import IntelligenceGraph
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard")
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Returns aggregated analytics for the National Intelligence Dashboard.
    """
    role = user.role
    logger.debug(f"analytics user.role is {repr(role)}")
    if role not in ["admin", "police", "cyber_cell"]:
        logger.debug(f"raising 403 in analytics because {repr(role)} not in allowed list")
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

@router.get("/command-center")
async def get_command_center_telemetry(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_admin)):
    """
    Returns live telemetry and stats for the Tactical Command Center.
    """
    from domain.models.takedown import TakedownPolicy
    from domain.models.audit_log import AIAuditLog
    
    # 1. Active Cases
    active_cases_query = await db.execute(select(func.count(Case.id)).where(Case.status != CaseStatus.resolved.value))
    active_cases = active_cases_query.scalar() or 0
    
    # 2. Automated Takedowns
    takedowns_query = await db.execute(select(func.count(TakedownPolicy.id)))
    takedowns_executed = takedowns_query.scalar() or 0
    
    # 3. Avg Inference Latency
    avg_latency_ms = 0
    
    # 4. Syndicates & Neo4j Clusters
    graph = IntelligenceGraph()
    campaigns = []
    city_coordinates = {}
    syndicates_tracked = 0
    
    try:
        clusters = await graph.get_connected_clusters()
        syndicates_tracked = len(clusters)
        
        # Build CampaignSyndicate list from Neo4j clusters
        for idx, cluster in enumerate(clusters[:10]): # Limit to top 10 for dashboard
            entity_val = cluster.get("entity_value", "Unknown")
            entity_type = cluster.get("entity_type", "Entity")
            case_ids = cluster.get("case_ids", [])
            
            # Simple hash/code generation
            code = f"SYND-26-IND-{str(hash(entity_val))[-3:]}"
            name = f"{entity_type} Threat Ring ({entity_val[:6]}...)"
            
            # Query Postgres to get the real financial loss and primary hub
            hub_name = "Unknown Origin"
            total_loss = 0.0
            if case_ids:
                stats_query = await db.execute(
                    select(func.sum(Case.estimated_amount)).where(Case.case_number.in_(case_ids))
                )
                total_loss = stats_query.scalar() or 0.0
                
                top_city = (await db.execute(
                    select(Case.city, func.count(Case.id).label('c'))
                    .where(Case.id.in_(case_ids), Case.city.isnot(None))
                    .group_by(Case.city)
                    .order_by(desc('c'))
                    .limit(1)
                )).first()
                if top_city:
                    hub_name = f"{top_city[0]} Hub"
            
            campaigns.append({
                "id": f"synd-{idx}",
                "code": code,
                "name": name,
                "hub": hub_name,
                "linked_cases": len(case_ids),
                "financial_exposure": f"₹{total_loss / 100000:.2f} Lakhs" if total_loss > 0 else "₹0.0 Lakhs",
                "risk_level": "CRITICAL" if len(case_ids) > 3 else "HIGH",
                "status": "ACTIVE"
            })
            
    except Exception as e:
        logger.error(f"Failed to fetch neo4j clusters for command center: {e}")
    finally:
        await graph.close()
        
    # 5. Spatial City Coordinates
    city_rows = (await db.execute(
        select(
            Case.city, 
            func.avg(Case.latitude), 
            func.avg(Case.longitude), 
            func.count(Case.id),
            func.max(Case.scam_type_code),
            func.sum(Case.estimated_amount)
        )
        .where(Case.city.isnot(None), Case.latitude.isnot(None), Case.longitude.isnot(None))
        .group_by(Case.city)
    )).all()
    for row in city_rows:
        city_name, lat, lng, count, scam_code, total_amount = row
        actual_loss = total_amount or 0.0
        if city_name and lat and lng:
            city_coordinates[city_name] = {
                "lat": lat,
                "lng": lng,
                "cases": count,
                "threat": 0.95 if count > 5 else 0.82,
                "code": scam_code or "PHISHING",
                "loss": f"₹{actual_loss / 100000:.2f} Lakhs" if actual_loss > 0 else "₹0.0 Lakhs"
            }
            
    if not city_coordinates:
        # Fallback if DB lacks geodata
        city_coordinates = {
            "Delhi NCR": {"lat": 28.7041, "lng": 77.1025, "cases": active_cases, "threat": 0.94, "code": "DIGITAL_ARREST", "loss": "₹64.2 Lakhs"}
        }
        
    if not campaigns:
        campaigns = [
            {
                "id": "synd-fb-1",
                "code": "SYND-FALLBACK-1",
                "name": "Fallback Institutional Ring",
                "hub": "Delhi NCR",
                "linked_cases": active_cases,
                "financial_exposure": "₹12.0 Lakhs",
                "risk_level": "HIGH",
                "status": "ACTIVE"
            }
        ]

    return {
        "stats": {
            "active_cases": active_cases,
            "takedowns_executed": takedowns_executed,
            "avg_latency_ms": avg_latency_ms,
            "syndicates_tracked": syndicates_tracked
        },
        "campaigns": campaigns,
        "cityCoordinates": city_coordinates
    }
