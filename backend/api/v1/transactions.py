import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, Request, BackgroundTasks,
    WebSocket, WebSocketDisconnect
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import selectinload

from infrastructure.db.session import get_db
from api.deps import get_current_user, get_current_user_optional
from domain.models.user import User
from domain.models.transaction import (
    Transaction,
    TransactionFeature,
    TransactionScore,
    TransactionDecision,
    DeviceProfile,
    BeneficiaryProfile,
    TransactionFeedback,
    TransactionStatus,
    FrictionAction,
    RiskBand,
    FeedbackDecision
)
from transaction.schemas import (
    TransactionCreate,
    TransactionRead,
    RiskScoreResponse,
    ExplanationResponse,
    ReviewRequest,
    RiskFeedItem
)
from domain.agents.transaction_agent import TransactionAgent
from infrastructure.graph.neo4j_client import IntelligenceGraph
from transaction.stream_manager import stream_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False


async def _get_txn_by_id_or_code(db: AsyncSession, identifier: str) -> Optional[Transaction]:
    """Find transaction by UUID primary key or by transaction_id string."""
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.score),
            selectinload(Transaction.decision),
            selectinload(Transaction.features),
            selectinload(Transaction.feedbacks)
        )
    )
    if _is_valid_uuid(identifier):
        query = query.where(
            or_(Transaction.id == uuid.UUID(identifier), Transaction.transaction_id == identifier)
        )
    else:
        query = query.where(Transaction.transaction_id == identifier)

    result = await db.execute(query)
    return result.scalar_one_or_none()


# ----------------------------------------------------------------------
# 1. Ingestion & Real-Time Decisioning
# ----------------------------------------------------------------------
@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def ingest_transaction(
    payload: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Ingests an incoming transaction, evaluates risk deterministically across
    features, graph patterns, and attack DNA, applies adaptive friction,
    persists records in PostgreSQL, and updates Neo4j.
    """
    txn_id_str = payload.transaction_id or f"TXN-{uuid.uuid4().hex[:10].upper()}"
    now = payload.timestamp or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Load historical transactions for this account (last 50)
    history_query = (
        select(Transaction)
        .where(Transaction.account_id == payload.account_id)
        .order_by(desc(Transaction.timestamp))
        .limit(50)
    )
    history_res = await db.execute(history_query)
    past_txns = history_res.scalars().all()
    account_history = [
        {
            "amount": float(t.amount),
            "timestamp": t.timestamp,
            "beneficiary_id": t.beneficiary_id,
            "device_id": t.device_id,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "channel": t.channel
        }
        for t in past_txns
    ]

    # 2. Fetch DeviceProfile if device_id provided
    device_profile_dict = None
    device_profile = None
    if payload.device_id:
        dev_res = await db.execute(select(DeviceProfile).where(DeviceProfile.device_id == payload.device_id))
        device_profile = dev_res.scalar_one_or_none()
        if device_profile:
            device_profile_dict = {
                "device_id": device_profile.device_id,
                "risk_score": device_profile.risk_score,
                "is_emulator": device_profile.is_emulator,
                "associated_accounts": device_profile.associated_accounts or [],
                "first_seen": device_profile.first_seen,
                "total_transactions": device_profile.total_transactions
            }

    # Merge client threat telemetry if provided in raw_metadata
    if payload.raw_metadata and "device_profile" in payload.raw_metadata:
        if device_profile_dict:
            device_profile_dict.update(payload.raw_metadata["device_profile"])
        else:
            device_profile_dict = dict(payload.raw_metadata["device_profile"])

    # 3. Fetch BeneficiaryProfile
    ben_res = await db.execute(
        select(BeneficiaryProfile).where(BeneficiaryProfile.beneficiary_id == payload.beneficiary_id)
    )
    beneficiary_profile = ben_res.scalar_one_or_none()
    beneficiary_profile_dict = None
    if beneficiary_profile:
        beneficiary_profile_dict = {
            "beneficiary_id": beneficiary_profile.beneficiary_id,
            "risk_score": beneficiary_profile.risk_score,
            "is_flagged": beneficiary_profile.is_flagged,
            "first_received_at": beneficiary_profile.first_received_at,
            "total_transactions": beneficiary_profile.total_transactions,
            "total_received_amount": beneficiary_profile.total_received_amount
        }

    # Merge client beneficiary intelligence if provided in raw_metadata
    if payload.raw_metadata and "beneficiary_profile" in payload.raw_metadata:
        if beneficiary_profile_dict:
            beneficiary_profile_dict.update(payload.raw_metadata["beneficiary_profile"])
        else:
            beneficiary_profile_dict = dict(payload.raw_metadata["beneficiary_profile"])

    # 4. Asynchronously evaluate Neo4j graph fraud rings
    graph_risk = 0.0
    graph_details = None
    try:
        graph = IntelligenceGraph()
        graph_details = await graph.get_transaction_fraud_ring(
            account_id=payload.account_id,
            device_id=payload.device_id,
            beneficiary_id=payload.beneficiary_id
        )
        graph_risk = graph_details.get("graph_risk_score", 0.0)
    except Exception as e:
        logger.warning(f"Neo4j graph evaluation skipped: {e}")

    if payload.raw_metadata and "graph_risk" in payload.raw_metadata:
        graph_risk = float(payload.raw_metadata["graph_risk"])

    # 5. Run TransactionAgent pipeline
    current_txn_dict = {
        "transaction_id": txn_id_str,
        "account_id": payload.account_id,
        "beneficiary_id": payload.beneficiary_id,
        "device_id": payload.device_id,
        "amount": payload.amount,
        "channel": payload.channel,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "timestamp": now,
        "city": payload.city,
        "state": payload.state
    }

    agent = TransactionAgent()
    analysis = await agent.analyze_transaction(
        current_txn=current_txn_dict,
        account_history=account_history,
        device_profile=device_profile_dict,
        beneficiary_profile=beneficiary_profile_dict,
        graph_risk_override=graph_risk
    )

    # 6. Map decision to transaction status
    decision_val = analysis["decision"]
    if decision_val == FrictionAction.APPROVE.value:
        txn_status = TransactionStatus.APPROVED.value
    elif decision_val == FrictionAction.APPROVE_AND_MONITOR.value:
        txn_status = TransactionStatus.APPROVED_AND_MONITORED.value
    elif decision_val == FrictionAction.STEP_UP_VERIFICATION.value:
        txn_status = TransactionStatus.STEP_UP_REQUIRED.value
    else:
        txn_status = TransactionStatus.HELD.value

    # 7. Persist Transaction
    new_txn = Transaction(
        transaction_id=txn_id_str,
        account_id=payload.account_id,
        beneficiary_id=payload.beneficiary_id,
        device_id=payload.device_id,
        amount=payload.amount,
        currency=payload.currency,
        transaction_type=payload.transaction_type,
        timestamp=now,
        latitude=payload.latitude,
        longitude=payload.longitude,
        city=payload.city,
        state=payload.state,
        channel=payload.channel,
        status=txn_status,
        raw_metadata={
            "attack_dna": analysis.get("attack_dna"),
            "graph_risk": graph_details,
            "custom_metadata": payload.raw_metadata or {}
        }
    )
    db.add(new_txn)
    await db.flush()

    # 8. Persist Features
    for fname, fval in analysis["features"].items():
        feat = TransactionFeature(
            transaction_id=new_txn.id,
            feature_name=fname,
            feature_value=float(fval),
            computed_at=now
        )
        db.add(feat)

    # 9. Persist Score
    score_rec = TransactionScore(
        transaction_id=new_txn.id,
        risk_score=analysis["risk_score"],
        confidence=analysis["confidence"],
        risk_band=analysis["risk_band"],
        sub_scores=analysis["sub_scores"],
        model_version="v1.0"
    )
    db.add(score_rec)

    # 10. Persist Decision
    decision_rec = TransactionDecision(
        transaction_id=new_txn.id,
        decision=decision_val,
        policy_version="v1.0",
        reason_codes=analysis["reason_codes"],
        explanation_text=analysis["explanation"]
    )
    db.add(decision_rec)

    # 11. Upsert DeviceProfile
    if payload.device_id:
        if device_profile:
            device_profile.last_seen = now
            device_profile.total_transactions += 1
            assoc = set(device_profile.associated_accounts or [])
            assoc.add(payload.account_id)
            device_profile.associated_accounts = list(assoc)
        else:
            new_dev = DeviceProfile(
                device_id=payload.device_id,
                first_seen=now,
                last_seen=now,
                total_transactions=1,
                associated_accounts=[payload.account_id],
                risk_score=0.0
            )
            db.add(new_dev)

    # 12. Upsert BeneficiaryProfile
    if beneficiary_profile:
        beneficiary_profile.last_received_at = now
        beneficiary_profile.total_transactions += 1
        beneficiary_profile.total_received_amount += payload.amount
    else:
        new_ben = BeneficiaryProfile(
            beneficiary_id=payload.beneficiary_id,
            first_received_at=now,
            last_received_at=now,
            total_received_amount=payload.amount,
            total_transactions=1,
            is_flagged=False,
            risk_score=0.0
        )
        db.add(new_ben)

    await db.commit()

    # 13. Asynchronously record into Neo4j graph in background
    async def _bg_graph_record():
        try:
            g = IntelligenceGraph()
            await g.record_transaction_graph(
                account_id=payload.account_id,
                transaction_id=txn_id_str,
                amount=payload.amount,
                beneficiary_id=payload.beneficiary_id,
                device_id=payload.device_id,
                channel=payload.channel,
                timestamp=now
            )
        except Exception as err:
            logger.warning(f"Background Neo4j graph recording failed: {err}")

    background_tasks.add_task(_bg_graph_record)

    # 14. Broadcast real-time transaction event to connected bankers (WebSocket & SSE)
    stream_payload = {
        "id": str(new_txn.id),
        "transaction_id": txn_id_str,
        "account_id": payload.account_id,
        "beneficiary_id": payload.beneficiary_id,
        "device_id": payload.device_id,
        "amount": float(payload.amount),
        "currency": payload.currency,
        "transaction_type": payload.transaction_type,
        "timestamp": now.isoformat(),
        "status": txn_status,
        "decision": decision_val,
        "risk_score": analysis["risk_score"],
        "risk_band": analysis["risk_band"],
        "confidence": analysis["confidence"],
        "top_reason_code": analysis["reason_codes"][0] if analysis["reason_codes"] else None,
        "reason_codes": analysis["reason_codes"],
        "attack_dna": analysis["attack_dna"]
    }
    background_tasks.add_task(stream_manager.broadcast, "TRANSACTION_INGESTED", stream_payload)

    return {
        "id": str(new_txn.id),
        "transaction_id": txn_id_str,
        "status": txn_status,
        "decision": decision_val,
        "risk_score": analysis["risk_score"],
        "risk_band": analysis["risk_band"],
        "confidence": analysis["confidence"],
        "reason_codes": analysis["reason_codes"],
        "explanation": analysis["explanation"],
        "attack_dna": analysis["attack_dna"],
        "signals": analysis["signals"],
        "sub_scores": analysis["sub_scores"]
    }


# ----------------------------------------------------------------------
# 2. Re-analyze / LLM Enrichment On Demand
# ----------------------------------------------------------------------
@router.post("/{id}/analyze", response_model=Dict[str, Any])
async def analyze_transaction_on_demand(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    On-demand deep analysis and LLM explanation enrichment for an existing transaction.
    Invokes local Ollama (or Groq) to generate an investigator brief.
    """
    txn = await _get_txn_by_id_or_code(db, id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {id} not found")

    reason_codes = txn.decision.reason_codes if txn.decision else []
    base_explanation = txn.decision.explanation_text if txn.decision else "Standard transaction processing."
    current_txn_dict = {
        "amount": float(txn.amount),
        "channel": txn.channel,
        "transaction_id": txn.transaction_id
    }

    enriched_narrative = None
    try:
        agent = TransactionAgent()
        enriched_narrative = await agent.enrich_explanation(
            current_txn=current_txn_dict,
            reason_codes=reason_codes,
            base_explanation=base_explanation
        )

        if enriched_narrative and txn.decision:
            txn.decision.explanation_text = enriched_narrative
            await db.commit()
    except Exception as err:
        logger.warning(f"On-demand narrative enrichment fallback applied: {err}")
        enriched_narrative = base_explanation

    return {
        "id": str(txn.id),
        "transaction_id": txn.transaction_id,
        "status": txn.status,
        "decision": txn.decision.decision if txn.decision else "UNKNOWN",
        "risk_score": txn.score.risk_score if txn.score else 0.0,
        "risk_band": txn.score.risk_band if txn.score else "LOW",
        "confidence": txn.score.confidence if txn.score else 0.5,
        "reason_codes": reason_codes,
        "explanation": enriched_narrative or base_explanation,
        "sub_scores": txn.score.sub_scores if txn.score else {},
        "raw_metadata": txn.raw_metadata or {}
    }


# ----------------------------------------------------------------------
# 3. Detailed Risk Breakdown
# ----------------------------------------------------------------------
@router.get("/{id}/risk", response_model=RiskScoreResponse)
async def get_transaction_risk(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Returns granular risk score, band, confidence, and sub-score metrics."""
    txn = await _get_txn_by_id_or_code(db, id)
    if not txn or not txn.score:
        raise HTTPException(status_code=404, detail=f"Risk score for transaction {id} not found")

    return RiskScoreResponse(
        transaction_id=txn.transaction_id,
        risk_score=float(txn.score.risk_score),
        confidence=float(txn.score.confidence),
        risk_band=txn.score.risk_band,
        sub_scores=txn.score.sub_scores or {},
        model_version=txn.score.model_version
    )


# ----------------------------------------------------------------------
# 4. Explainability Endpoint
# ----------------------------------------------------------------------
@router.get("/{id}/explanation", response_model=ExplanationResponse)
async def get_transaction_explanation(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """Returns deterministic reason codes, narrative brief, Attack DNA and graph signals."""
    txn = await _get_txn_by_id_or_code(db, id)
    if not txn or not txn.decision:
        raise HTTPException(status_code=404, detail=f"Explanation for transaction {id} not found")

    attack_dna = (txn.raw_metadata or {}).get("attack_dna")
    graph_risk = (txn.raw_metadata or {}).get("graph_risk")

    return ExplanationResponse(
        transaction_id=txn.transaction_id,
        risk_score=float(txn.score.risk_score) if txn.score else 0.0,
        confidence=float(txn.score.confidence) if txn.score else 0.5,
        decision=txn.decision.decision,
        reason_codes=txn.decision.reason_codes or [],
        explanation_text=txn.decision.explanation_text or "No detailed explanation recorded.",
        sub_scores=txn.score.sub_scores if txn.score else {},
        attack_dna_match=attack_dna,
        graph_risk=graph_risk
    )


# ----------------------------------------------------------------------
# 5. Human Feedback & Decision Review
# ----------------------------------------------------------------------
@router.post("/{id}/review", response_model=Dict[str, Any])
async def review_transaction(
    id: str,
    payload: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Records banker / fraud analyst human review (CONFIRMED_FRAUD, FALSE_POSITIVE,
    LEGITIMATE_ANOMALY). Updates transaction status and propagates feedback to
    beneficiary and device profiles for online learning.
    """
    txn = await _get_txn_by_id_or_code(db, id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {id} not found")

    decision_input = payload.human_decision.strip().upper()
    if decision_input not in [d.value for d in FeedbackDecision]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{decision_input}'. Allowed: {[d.value for d in FeedbackDecision]}"
        )

    investigator = payload.investigator_id or user.email or str(user.id)
    ai_risk = float(txn.score.risk_score) if txn.score else 0.5
    ai_decision = txn.decision.decision if txn.decision else "APPROVE"

    feedback = TransactionFeedback(
        transaction_id=txn.id,
        investigator_id=investigator,
        ai_risk_score=ai_risk,
        ai_decision=ai_decision,
        human_decision=decision_input,
        notes=payload.notes,
        created_at=datetime.now(timezone.utc)
    )
    db.add(feedback)

    # Propagate outcome to transaction status and entity profiles
    if decision_input == FeedbackDecision.CONFIRMED_FRAUD.value:
        txn.status = TransactionStatus.REJECTED.value
        # Flag beneficiary
        ben_res = await db.execute(select(BeneficiaryProfile).where(BeneficiaryProfile.beneficiary_id == txn.beneficiary_id))
        ben = ben_res.scalar_one_or_none()
        if ben:
            ben.is_flagged = True
            ben.risk_score = 0.95
        # Escalate device risk
        if txn.device_id:
            dev_res = await db.execute(select(DeviceProfile).where(DeviceProfile.device_id == txn.device_id))
            dev = dev_res.scalar_one_or_none()
            if dev:
                dev.risk_score = max(dev.risk_score, 0.90)

    elif decision_input == FeedbackDecision.FALSE_POSITIVE.value:
        txn.status = TransactionStatus.APPROVED.value
        # Ease beneficiary flag if it was false positive
        ben_res = await db.execute(select(BeneficiaryProfile).where(BeneficiaryProfile.beneficiary_id == txn.beneficiary_id))
        ben = ben_res.scalar_one_or_none()
        if ben and not ben.is_flagged:
            ben.risk_score = max(0.0, ben.risk_score - 0.20)

    elif decision_input == FeedbackDecision.LEGITIMATE_ANOMALY.value:
        txn.status = TransactionStatus.APPROVED.value

    await db.commit()

    # Broadcast review event to all connected monitors
    await stream_manager.broadcast("TRANSACTION_REVIEWED", {
        "transaction_id": txn.transaction_id,
        "human_decision": decision_input,
        "new_status": txn.status,
        "investigator_id": investigator,
        "recorded_at": feedback.created_at.isoformat()
    })

    return {
        "status": "success",
        "transaction_id": txn.transaction_id,
        "human_decision": decision_input,
        "new_status": txn.status,
        "investigator_id": investigator,
        "recorded_at": feedback.created_at.isoformat()
    }


# ----------------------------------------------------------------------
# 6. Live Risk Feed for Real-Time Monitoring
# ----------------------------------------------------------------------
@router.get("/risk-feed", response_model=Dict[str, Any])
async def get_risk_feed(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    risk_band: Optional[str] = Query(None, description="Filter by risk band: LOW, GUARDED, ELEVATED, HIGH, CRITICAL"),
    status: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, HELD, REJECTED"),
    account_id: Optional[str] = Query(None, description="Filter by source account"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Paginated real-time monitoring feed for the banker transactions dashboard.
    Returns latest transactions joined with risk score and action decision.
    """
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.score),
            selectinload(Transaction.decision)
        )
        .order_by(desc(Transaction.timestamp))
    )

    if account_id:
        query = query.where(Transaction.account_id == account_id.strip())
    if status:
        query = query.where(Transaction.status == status.strip().upper())
    if risk_band:
        query = query.join(TransactionScore).where(TransactionScore.risk_band == risk_band.strip().upper())

    # Count total
    count_query = select(func.count(Transaction.id))
    if account_id:
        count_query = count_query.where(Transaction.account_id == account_id.strip())
    if status:
        count_query = count_query.where(Transaction.status == status.strip().upper())
    if risk_band:
        count_query = count_query.join(TransactionScore).where(TransactionScore.risk_band == risk_band.strip().upper())

    total_count = (await db.execute(count_query)).scalar() or 0

    paginated_query = query.offset(offset).limit(limit)
    records = (await db.execute(paginated_query)).scalars().all()

    items: List[RiskFeedItem] = []
    for t in records:
        score_val = float(t.score.risk_score) if t.score else 0.0
        conf_val = float(t.score.confidence) if t.score else 0.5
        band_val = t.score.risk_band if t.score else RiskBand.LOW.value
        dec_val = t.decision.decision if t.decision else FrictionAction.APPROVE.value
        top_reason = t.decision.reason_codes[0] if (t.decision and t.decision.reason_codes) else None

        items.append(
            RiskFeedItem(
                id=str(t.id),
                transaction_id=t.transaction_id,
                account_id=t.account_id,
                beneficiary_id=t.beneficiary_id,
                amount=float(t.amount),
                transaction_type=t.transaction_type,
                timestamp=t.timestamp,
                risk_score=score_val,
                confidence=conf_val,
                risk_band=band_val,
                decision=dec_val,
                top_reason_code=top_reason
            )
        )

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "items": [item.model_dump() for item in items]
    }


# ----------------------------------------------------------------------
# 7. Attack Campaign Waves Aggregator
# ----------------------------------------------------------------------
@router.get("/campaigns", response_model=Dict[str, Any])
async def get_attack_campaigns(
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Aggregates recent transactions by coordinated Attack DNA signatures
    to identify emerging fraud waves across the banking network.
    """
    # Fetch recent high-risk transactions
    query = (
        select(Transaction)
        .options(
            selectinload(Transaction.score),
            selectinload(Transaction.decision)
        )
        .order_by(desc(Transaction.timestamp))
        .limit(200)
    )
    result = await db.execute(query)
    txns = result.scalars().all()

    campaigns_map: Dict[str, Dict[str, Any]] = {}

    for t in txns:
        dna = (t.raw_metadata or {}).get("attack_dna")
        if dna and dna.get("matched"):
            dna_id = dna.get("dna_id", "UNKNOWN-DNA")
            if dna_id not in campaigns_map:
                campaigns_map[dna_id] = {
                    "dna_id": dna_id,
                    "dna_name": dna.get("dna_name", dna_id),
                    "description": dna.get("description"),
                    "severity": dna.get("severity", 0.8),
                    "transaction_count": 0,
                    "total_amount_at_risk": 0.0,
                    "unique_accounts": set(),
                    "unique_beneficiaries": set(),
                    "first_detected": t.timestamp,
                    "last_detected": t.timestamp,
                    "sample_transactions": []
                }

            camp = campaigns_map[dna_id]
            camp["transaction_count"] += 1
            camp["total_amount_at_risk"] += float(t.amount)
            camp["unique_accounts"].add(t.account_id)
            camp["unique_beneficiaries"].add(t.beneficiary_id)
            if t.timestamp < camp["first_detected"]:
                camp["first_detected"] = t.timestamp
            if t.timestamp > camp["last_detected"]:
                camp["last_detected"] = t.timestamp

            if len(camp["sample_transactions"]) < 5:
                camp["sample_transactions"].append({
                    "transaction_id": t.transaction_id,
                    "account_id": t.account_id,
                    "beneficiary_id": t.beneficiary_id,
                    "amount": float(t.amount),
                    "timestamp": t.timestamp.isoformat()
                })

    formatted_campaigns = []
    for c in campaigns_map.values():
        formatted_campaigns.append({
            "dna_id": c["dna_id"],
            "dna_name": c["dna_name"],
            "description": c["description"],
            "severity": c["severity"],
            "transaction_count": c["transaction_count"],
            "total_amount_at_risk": round(c["total_amount_at_risk"], 2),
            "unique_accounts_count": len(c["unique_accounts"]),
            "unique_beneficiaries_count": len(c["unique_beneficiaries"]),
            "first_detected": c["first_detected"].isoformat(),
            "last_detected": c["last_detected"].isoformat(),
            "sample_transactions": c["sample_transactions"]
        })

    formatted_campaigns.sort(key=lambda x: x["total_amount_at_risk"], reverse=True)

    return {
        "campaign_count": len(formatted_campaigns),
        "campaigns": formatted_campaigns
    }


# ----------------------------------------------------------------------
# 8. Account Risk Network Graph (Cytoscape Visualization)
# ----------------------------------------------------------------------
@router.get("/accounts/{account_id}/risk-network", response_model=Dict[str, Any])
async def get_account_risk_network(
    account_id: str,
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Returns 2-hop graph neighborhood for an account formatted for Cytoscape.js,
    visualizing linked transactions, beneficiaries, and shared device networks.
    """
    try:
        graph = IntelligenceGraph()
        network = await graph.get_account_risk_network(account_id=account_id.strip())
        return network
    except Exception as e:
        logger.error(f"Error querying risk network for account {account_id}: {e}")
        return {"nodes": [], "edges": [], "error": str(e)}


# ----------------------------------------------------------------------
# 9. Complete Transaction Detail (Forensic Cockpit)
# ----------------------------------------------------------------------
@router.get("/{id}", response_model=Dict[str, Any])
async def get_transaction_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Returns full transaction record joined with risk score, friction decision,
    feature vector, historical feedback, and metadata for the forensic cockpit.
    """
    txn = await _get_txn_by_id_or_code(db, id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {id} not found")

    features_dict = {f.feature_name: float(f.feature_value) for f in (txn.features or [])}
    feedbacks_list = [
        {
            "id": str(fb.id),
            "investigator_id": fb.investigator_id,
            "ai_risk_score": float(fb.ai_risk_score),
            "ai_decision": fb.ai_decision,
            "human_decision": fb.human_decision,
            "notes": fb.notes,
            "created_at": fb.created_at.isoformat() if fb.created_at else None
        }
        for fb in (txn.feedbacks or [])
    ]

    return {
        "id": str(txn.id),
        "transaction_id": txn.transaction_id,
        "account_id": txn.account_id,
        "beneficiary_id": txn.beneficiary_id,
        "device_id": txn.device_id,
        "amount": float(txn.amount),
        "currency": txn.currency,
        "transaction_type": txn.transaction_type,
        "timestamp": txn.timestamp.isoformat() if txn.timestamp else None,
        "status": txn.status,
        "latitude": txn.latitude,
        "longitude": txn.longitude,
        "city": txn.city,
        "state": txn.state,
        "channel": txn.channel,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
        "risk_score": float(txn.score.risk_score) if txn.score else 0.0,
        "confidence": float(txn.score.confidence) if txn.score else 0.5,
        "risk_band": txn.score.risk_band if txn.score else "LOW",
        "sub_scores": txn.score.sub_scores if txn.score else {},
        "model_version": txn.score.model_version if txn.score else "v1.0",
        "decision": txn.decision.decision if txn.decision else "APPROVE",
        "reason_codes": txn.decision.reason_codes if txn.decision else [],
        "explanation": txn.decision.explanation_text if txn.decision else "Standard transaction processing.",
        "features": features_dict,
        "raw_metadata": txn.raw_metadata or {},
        "feedbacks": feedbacks_list
    }


# ----------------------------------------------------------------------
# 10. Real-Time Streaming: WebSockets & Server-Sent Events (SSE)
# ----------------------------------------------------------------------
@router.websocket("/ws")
async def websocket_transaction_stream(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Bi-directional WebSocket streaming endpoint for real-time transaction
    ingestion and human review status updates.
    """
    await stream_manager.connect_ws(websocket)
    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg_data = json.loads(raw_msg)
                action_type = msg_data.get("type", "").upper()
                if action_type == "PING":
                    await websocket.send_text(json.dumps({
                        "type": "PONG",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))
            except json.JSONDecodeError:
                if raw_msg.strip().upper() == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG"}))
    except WebSocketDisconnect:
        await stream_manager.disconnect_ws(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        await stream_manager.disconnect_ws(websocket)


@router.get("/stream")
async def sse_transaction_stream(request: Request):
    """
    Server-Sent Events (SSE) HTTP endpoint for clients that cannot use WebSockets.
    Streams transaction events as 'text/event-stream'.
    """
    queue = await stream_manager.connect_sse()

    async def event_generator():
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            await stream_manager.disconnect_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

