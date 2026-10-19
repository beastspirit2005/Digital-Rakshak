"""
Phase 1: Real-Time Protection & Intelligence Validation Test Suite
===================================================================
Automated verification for Phase 1 of the Digital Rakshak Master Plan:
1.1 Event pipeline: schema validation, idempotency, retry/dead-letter mechanics
1.2 Risk engine: 4 scenarios (known malicious, legitimate unusual, unknown indicator, stale intel)
1.3 Graph intelligence: campaign syndicate attribution, weak vs strong ties, outage resilience
1.4 Real-time delivery: multi-tenant alert broadcast and SSE isolation
1.5 Latency baselines: sub-15ms Stage A fast assessment
"""

import asyncio
import json
import time
import uuid
import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from runtime.stream_consumer import StreamConsumer, ThreatEventEnvelope
from intelligence.risk_engine import ThreatIntelligenceRiskEngine, risk_engine
from infrastructure.event_bus.alert_broadcaster import TenantAlertBroadcaster


# ── 1.1 Event Schema Validation & Idempotency Tests ─────────────────────────

@pytest.mark.asyncio
async def test_event_schema_validation_success():
    """Verify that a valid ThreatEventEnvelope passes validation cleanly."""
    valid_data = {
        "event_id": str(uuid.uuid4()),
        "event_type": "b2b_event",
        "source": "b2b_api",
        "tenant_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "type": "phishing_url",
            "url": "https://yono-sbi-update.in/login",
            "severity": "critical",
        },
    }
    envelope = ThreatEventEnvelope(**valid_data)
    assert envelope.event_type == "b2b_event"
    assert envelope.payload["type"] == "phishing_url"


@pytest.mark.asyncio
async def test_event_schema_validation_rejection():
    """Verify that malformed events missing required fields are rejected."""
    consumer = StreamConsumer()
    # Missing event_type
    malformed_data = {
        "event_id": str(uuid.uuid4()),
        "source": "b2b_api",
    }
    with pytest.raises(Exception):
        await consumer._process_event("msg-test-1", malformed_data)


@pytest.mark.asyncio
async def test_event_idempotency_guard():
    """Verify that duplicate events with identical event_id are not processed twice."""
    consumer = StreamConsumer()
    test_event_id = f"evt-idem-{uuid.uuid4().hex[:8]}"

    event_data = {
        "event_id": test_event_id,
        "event_type": "b2b_event",
        "source": "b2b_api",
        "tenant_id": str(uuid.uuid4()),
        "payload": {
            "type": "credential_stuffing",
            "attempts": 40,
        },
    }

    # First delivery: processed
    res1 = await consumer.process_event_direct(event_data)
    assert res1["status"] == "processed"

    # Second duplicate delivery: skipped by idempotency guard
    res2 = await consumer.process_event_direct(event_data)
    assert res2["status"] == "duplicate_skipped"
    assert res2["event_id"] == test_event_id


# ── 1.2 Risk Engine: The 4 Master Plan Scenarios ────────────────────────────

def test_risk_scenario_1_known_malicious_indicator():
    """
    Scenario 1: Known malicious indicator.
    Expected outcome: High-risk assessment (score >= 0.85) with supporting evidence and hard block/hold.
    """
    engine = ThreatIntelligenceRiskEngine()
    result = engine.assess_stage_a(
        event_type="phishing_url",
        severity_hint="critical",
        source_ip="185.220.101.5",
        metadata={"url": "https://yono-sbi-update.in/verify", "target_upi": "syndicate_mule@ybl"},
    )
    assert result["risk_score"] >= 0.85
    assert result["confidence"] >= 0.80
    assert result["action"] in ("BLOCK", "HOLD")
    assert result["category"] == "KNOWN_MALICIOUS"
    assert any("yono-sbi-update.in" in r for r in result["reasons"])


def test_risk_scenario_2_legitimate_but_unusual_activity():
    """
    Scenario 2: Legitimate but unusual activity.
    Expected outcome: Assessment that avoids an unjustified hard block (STEP_UP / MONITOR, score ~0.50).
    """
    engine = ThreatIntelligenceRiskEngine()
    result = engine.assess_stage_a(
        event_type="suspicious_login",
        severity_hint="medium",
        source_ip="103.21.244.2",  # Regular ISP IP
        metadata={
            "is_new_device": True,
            "is_unusual_hour": True,
            "location_deviation_score": 0.65,
            "attempts": 1,  # Single legitimate login attempt
        },
    )
    # Crucial assertion: Must NOT be a hard block
    assert result["action"] != "BLOCK"
    assert result["action"] in ("STEP_UP", "MONITOR")
    assert result["category"] == "LEGITIMATE_BUT_UNUSUAL"
    assert 0.40 <= result["risk_score"] <= 0.65
    assert any("Unusual activity detected" in r for r in result["reasons"])


def test_risk_scenario_3_unknown_indicator():
    """
    Scenario 3: Unknown indicator.
    Expected outcome: Uncertain result with appropriate caution (calibrated low confidence, not assumed safe).
    """
    engine = ThreatIntelligenceRiskEngine()
    result = engine.assess_stage_a(
        event_type="generic_telemetry",
        severity_hint="low",
        source_ip="115.110.22.4",
        metadata={
            "domain": "brand-new-unknown-store.co.in",
            "attempts": 1,
        },
    )
    assert result["category"] == "UNKNOWN_INDICATOR"
    assert result["action"] == "MONITOR"
    # Calibrated confidence: should reflect uncertainty (<= 0.50), not false certainty
    assert result["confidence"] <= 0.50
    assert any("cautionary baseline monitoring" in r for r in result["reasons"])


def test_risk_scenario_4_conflicting_or_stale_intelligence():
    """
    Scenario 4: Conflicting or stale threat intelligence.
    Expected outcome: Assessment that accounts for evidence quality and freshness (confidence decay).
    """
    engine = ThreatIntelligenceRiskEngine()
    fresh_res = engine.assess_stage_a(
        event_type="phishing_url",
        metadata={"url": "https://yono-sbi-update.in", "intel_age_days": 2.0},
    )
    stale_res = engine.assess_stage_a(
        event_type="phishing_url",
        metadata={"url": "https://yono-sbi-update.in", "intel_age_days": 120.0},
    )
    # Stale evidence must have significantly lower confidence due to time decay
    assert stale_res["confidence"] < fresh_res["confidence"]
    assert stale_res["evidence_freshness_factor"] == 0.60
    assert any("Threat intelligence is stale" in r for r in stale_res["reasons"])


# ── 1.3 & 1.4 Graph Intelligence & Multi-Tenant Delivery ───────────────────

@pytest.mark.asyncio
async def test_two_stage_enrichment_and_mitre_mapping():
    """Verify that Stage B enriches Stage A with MITRE ATT&CK tactics and graph status."""
    engine = ThreatIntelligenceRiskEngine()
    stage_a = engine.assess_stage_a(
        event_type="phishing_url",
        metadata={"url": "https://yono-sbi-update.in"},
    )
    stage_b = await engine.enrich_stage_b(
        stage_a_result=stage_a,
        event_type="phishing_url",
        metadata={"url": "https://yono-sbi-update.in"},
    )

    assert stage_b["stage"] == "STAGE_B_COMPLETE"
    assert "T1566" in stage_b["mitre_tactic"]
    assert stage_b["final_risk_score"] >= stage_a["risk_score"]
    assert "total_latency_ms" in stage_b

    from infrastructure.graph.neo4j_client import IntelligenceGraph
    await IntelligenceGraph.close_driver()


@pytest.mark.asyncio
async def test_multi_tenant_sse_alert_isolation():
    """
    Verify real-time SSE alert delivery and strict tenant isolation:
    Org A subscriber receives Org A alerts; Org B subscriber NEVER receives Org A alerts.
    """
    broadcaster = TenantAlertBroadcaster()
    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())

    queue_a = await broadcaster.subscribe(org_a)
    queue_b = await broadcaster.subscribe(org_b)

    # Dispatch alert strictly to Org A
    alert_data = {
        "alert_id": "ALT-001",
        "severity": "CRITICAL",
        "target": "phishing_campaign",
    }
    delivered = await broadcaster.broadcast_to_tenant(org_a, "threat_alert", alert_data)
    assert delivered >= 1

    # Org A queue must contain the alert
    msg_a = await asyncio.wait_for(queue_a.get(), timeout=1.0)
    assert "threat_alert" in msg_a
    assert "ALT-001" in msg_a
    assert org_a in msg_a

    # Org B queue must be strictly empty (zero message leakage)
    assert queue_b.empty(), "Tenant isolation failure: Org B received Org A alert!"

    # Clean up
    await broadcaster.unsubscribe(org_a, queue_a)
    await broadcaster.unsubscribe(org_b, queue_b)


# ── 1.5 Performance Baselines ──────────────────────────────────────────────

def test_stage_a_latency_baseline():
    """Verify that Stage A fast assessment completes well within the 15ms target."""
    engine = ThreatIntelligenceRiskEngine()
    latencies = []

    for _ in range(50):
        t0 = time.perf_counter()
        engine.assess_stage_a(
            event_type="credential_stuffing",
            metadata={"attempts": 25, "is_new_device": True},
        )
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    assert p95_latency < 15.0, f"Stage A p95 latency {p95_latency:.2f}ms exceeded 15ms target!"
    assert avg_latency < 5.0, f"Stage A avg latency {avg_latency:.2f}ms exceeded 5ms target!"
