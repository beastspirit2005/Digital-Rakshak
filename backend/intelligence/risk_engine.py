"""
Two-Stage Threat Intelligence Risk Engine
==========================================
Engine implementing Phase 1.2 specifications:
* Stage A: Fast Assessment (< 10 ms) — cached reputation, deterministic rules, calibrated confidence.
* Stage B: Enrichment (< 200 ms) — Neo4j graph correlation, campaign syndicate attribution, policy decision.

Supports 4 core event scenarios:
1. Known malicious indicator -> High-risk assessment (score >= 0.85) + hard block/hold.
2. Legitimate but unusual activity -> Proportional friction (STEP_UP / MONITOR), avoiding unjustified blocks.
3. Unknown indicator -> Cautionary classification with calibrated low confidence (not assumed safe or guilty).
4. Conflicting or stale intelligence -> Confidence decay accounting for evidence age and source credibility.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Canonical MITRE ATT&CK mappings
MITRE_MAPPINGS = {
    "phishing_url": "MITRE T1566.002 (Phishing: Spearphishing Link)",
    "credential_stuffing": "MITRE T1110.004 (Brute Force: Credential Stuffing)",
    "mule_transfer": "MITRE T1584.004 (Resource Development: Server / Mule Proxy)",
    "fake_refund_desk": "MITRE T1566.004 (Phishing: Voice / Vishing Lure)",
    "token_theft": "MITRE T1539 (Steal Web Session Cookie)",
    "urgent_lure": "MITRE T1204 (User Execution: Malicious Coercion)",
}

# Known malicious indicators (Seed blocklist / OSINT high-confidence cache)
KNOWN_MALICIOUS_DOMAINS = {
    "yono-sbi-update.in",
    "secure-hdfc-kyc-verification.ru",
    "apk-rakshak-malware.top",
    "fake-gpay.com",
    "refund-desk-support.xyz",
}

KNOWN_MALICIOUS_IPS = {
    "185.220.101.5",   # Tor exit node with active phishing history
    "194.26.29.112",   # Known bulletproof hosting
    "45.154.255.88",   # C2 gateway
}

KNOWN_MALICIOUS_UPIS = {
    "syndicate_mule@ybl",
    "phishing_refund@okaxis",
    "fake_lottery_desk@icici",
}


class ThreatIntelligenceRiskEngine:
    """
    Two-stage risk scoring engine combining fast deterministic heuristics with
    deep graph intelligence correlation.
    """

    def __init__(self, model_version: str = "v2.1-hybrid"):
        self.model_version = model_version

    # --------------------------------------------------------------------------
    # Stage A: Fast Assessment (< 10ms)
    # --------------------------------------------------------------------------
    def assess_stage_a(
        self,
        event_type: str,
        severity_hint: str = "medium",
        source_ip: Optional[str] = None,
        source_user: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stage A: Instant deterministic heuristic & reputation assessment.
        Returns preliminary risk score, friction action, and calibrated confidence.
        """
        start_time = time.perf_counter()
        meta = metadata or {}
        reasons: List[str] = []
        is_known_malicious = False
        is_unusual_activity = False
        is_unknown_indicator = True
        evidence_freshness_factor = 1.0

        target_url = str(meta.get("url") or "").lower()
        target_domain = str(meta.get("domain") or "").lower()
        target_upi = str(meta.get("target_upi") or meta.get("upi") or "").lower()
        attempts = int(meta.get("attempts") or 0)
        intelligence_age_days = float(meta.get("intel_age_days") or 0.0)

        # 1. Evidence Freshness Decay (Scenario 4)
        if intelligence_age_days > 90:
            evidence_freshness_factor = 0.60
            reasons.append(f"Threat intelligence is stale ({int(intelligence_age_days)} days old); applied 40% confidence decay")
        elif intelligence_age_days > 30:
            evidence_freshness_factor = 0.85
            reasons.append(f"Threat intelligence is aged ({int(intelligence_age_days)} days old); applied 15% confidence decay")

        # 2. Known Malicious Indicator Check (Scenario 1)
        for d in KNOWN_MALICIOUS_DOMAINS:
            if d in target_url or d == target_domain:
                is_known_malicious = True
                reasons.append(f"Matches verified malicious phishing domain '{d}'")
                break

        if source_ip in KNOWN_MALICIOUS_IPS:
            is_known_malicious = True
            reasons.append(f"Source IP '{source_ip}' belongs to high-risk malicious infrastructure")

        if target_upi in KNOWN_MALICIOUS_UPIS:
            is_known_malicious = True
            reasons.append(f"Target UPI '{target_upi}' is flagged in central fraud mule registry")

        # 3. Legitimate but Unusual Activity Check (Scenario 2)
        if not is_known_malicious:
            # Check for benign anomaly patterns (e.g., travel location, unusual hour, single new device)
            is_new_device = meta.get("is_new_device") is True
            is_unusual_hour = meta.get("is_unusual_hour") is True
            location_deviation = float(meta.get("location_deviation_score") or 0.0)

            if (is_new_device or is_unusual_hour or location_deviation > 0.5) and attempts < 10:
                is_unusual_activity = True
                is_unknown_indicator = False
                reasons.append("Unusual activity detected (new device or abnormal access timing) but lacks malicious payload markers")

        # 4. Credential Stuffing / Brute Force Rate Check
        if attempts >= 20:
            is_known_malicious = True
            reasons.append(f"Automated brute-force attack detected ({attempts} attempts exceeding threshold of 20)")
        elif attempts >= 5 and not is_known_malicious:
            is_unusual_activity = True
            is_unknown_indicator = False
            reasons.append(f"Elevated authentication retry rate ({attempts} attempts)")

        # 5. Score & Action Calculation
        if is_known_malicious:
            risk_score = 0.92
            confidence = round(0.95 * evidence_freshness_factor, 2)
            action = "BLOCK" if risk_score >= 0.90 else "HOLD"
            category = "KNOWN_MALICIOUS"
        elif is_unusual_activity:
            # Crucial: Avoid unjustified hard block for legitimate but unusual actions
            risk_score = 0.52
            confidence = round(0.75 * evidence_freshness_factor, 2)
            action = "STEP_UP"  # Step-up verification / OTP challenge instead of hard block
            category = "LEGITIMATE_BUT_UNUSUAL"
        else:
            # Scenario 3: Unknown indicator — cautious, calibrated low confidence
            risk_score = 0.25
            confidence = round(0.35 * evidence_freshness_factor, 2)
            action = "MONITOR"
            category = "UNKNOWN_INDICATOR"
            reasons.append("Indicator not present in local reputation cache; proceeding with cautionary baseline monitoring")

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "stage": "STAGE_A_FAST",
            "model_version": self.model_version,
            "risk_score": risk_score,
            "confidence": confidence,
            "action": action,
            "category": category,
            "reasons": reasons,
            "evidence_freshness_factor": evidence_freshness_factor,
            "latency_ms": elapsed_ms,
        }

    # --------------------------------------------------------------------------
    # Stage B: Enrichment (< 200ms)
    # --------------------------------------------------------------------------
    async def enrich_stage_b(
        self,
        stage_a_result: Dict[str, Any],
        event_type: str,
        source_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Stage B: Graph intelligence correlation and MITRE ATT&CK contextual mapping.
        Updates the Stage A risk score and action based on graph topology.
        """
        start_time = time.perf_counter()
        meta = metadata or {}
        stage_a_score = stage_a_result["risk_score"]
        stage_a_action = stage_a_result["action"]
        reasons = list(stage_a_result.get("reasons", []))

        correlated_cases: List[str] = []
        syndicate_code: Optional[str] = None
        graph_status = "CONNECTED"

        # 1. Graph Intelligence Query (Neo4j)
        try:
            from infrastructure.graph.neo4j_client import IntelligenceGraph
            graph = IntelligenceGraph()

            target_upi = meta.get("target_upi") or meta.get("upi")
            target_url = meta.get("url")

            # Check if indicator links to existing cases in graph
            if target_upi:
                cases = await graph.get_related_cases("UPI_ID", str(target_upi))
                correlated_cases.extend(cases)
            if target_url:
                cases = await graph.get_related_cases("URL", str(target_url))
                correlated_cases.extend(cases)
            if source_ip and not correlated_cases:
                cases = await graph.get_related_cases("IPAddress", str(source_ip))
                # Single shared IP is treated as weak correlation (investigative signal, not proof of guilt)
                if len(cases) == 1:
                    reasons.append(f"Investigative signal: Shared IP with 1 prior case ({cases[0]}); treated as advisory correlation")
                elif len(cases) > 1:
                    correlated_cases.extend(cases)

        except Exception as exc:
            logger.warning("Graph correlation fallback during Stage B enrichment: %s", exc)
            graph_status = "DEGRADED_FALLBACK"

        # 2. Adjust Risk & Confidence based on Graph Topology
        final_risk_score = stage_a_score
        final_confidence = stage_a_result["confidence"]

        if len(correlated_cases) >= 2:
            syndicate_code = f"SYN-RING-{correlated_cases[0][:8].upper()}"
            final_risk_score = min(1.0, max(final_risk_score, 0.95))
            final_confidence = min(0.99, final_confidence + 0.15)
            stage_a_action = "BLOCK"
            reasons.append(f"High-confidence fraud syndicate match: Linked to {len(correlated_cases)} distinct victims in National Intelligence Graph ({syndicate_code})")
        elif len(correlated_cases) == 1:
            final_risk_score = min(1.0, final_risk_score + 0.15)
            final_confidence = min(0.95, final_confidence + 0.10)
            if stage_a_action == "MONITOR":
                stage_a_action = "STEP_UP"
            reasons.append(f"Graph intelligence: Entity linked to case {correlated_cases[0]}")

        # 3. MITRE ATT&CK Mapping
        mitre_tactic = MITRE_MAPPINGS.get(event_type, "MITRE T1078 (Valid Accounts / Unknown Vector)")

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        total_latency_ms = round(stage_a_result["latency_ms"] + elapsed_ms, 2)

        return {
            "stage": "STAGE_B_COMPLETE",
            "model_version": self.model_version,
            "stage_a": stage_a_result,
            "final_risk_score": round(final_risk_score, 4),
            "final_confidence": round(final_confidence, 2),
            "final_action": stage_a_action,
            "mitre_tactic": mitre_tactic,
            "correlated_cases": correlated_cases,
            "syndicate_code": syndicate_code,
            "graph_status": graph_status,
            "reasons": reasons,
            "enrichment_latency_ms": elapsed_ms,
            "total_latency_ms": total_latency_ms,
        }


# Global Singleton Instance
risk_engine = ThreatIntelligenceRiskEngine()
