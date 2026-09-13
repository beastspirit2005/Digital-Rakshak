from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta


KNOWN_ATTACK_DNA_TEMPLATES = [
    {
        "dna_id": "DNA-UPI-ACCOUNT-TAKEOVER-V1",
        "name": "UPI Account Takeover & Rapid Drain",
        "description": "New device enrollment followed by new beneficiary addition, micro-probe transfer, and rapid large drains.",
        "steps": [
            "NEW_DEVICE",
            "NEW_BENEFICIARY",
            "MICRO_PROBE",
            "LARGE_TRANSFER"
        ],
        "severity": 0.95
    },
    {
        "dna_id": "DNA-MULE-FAN-OUT-V1",
        "name": "Mule Dispersion Fan-Out",
        "description": "Rapid multi-beneficiary dispersal within short time window to avoid freeze limits.",
        "steps": [
            "BURST_VELOCITY",
            "MULTIPLE_BENEFICIARIES",
            "ROUND_AMOUNT_DRAIN"
        ],
        "severity": 0.90
    },
    {
        "dna_id": "DNA-NIGHT-SIPHON-V1",
        "name": "Off-Hours Sleep Siphoning",
        "description": "Exploiting citizen inactivity between 01:00 AM and 05:00 AM to transfer maximum daily limits.",
        "steps": [
            "UNUSUAL_HOURS",
            "NEW_DEVICE",
            "MAX_LIMIT_TRANSFER"
        ],
        "severity": 0.88
    }
]


class AttackDNAMatcher:
    """
    Evaluates transaction history to detect signatures of coordinated cyber attacks 
    and account takeover behavior sequences.
    """

    def evaluate(
        self,
        current_txn: Dict[str, Any],
        features: Dict[str, float],
        account_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Matches recent account activity against known Attack DNA sequence templates.
        
        :return: {
            "matched": bool,
            "dna_id": Optional[str],
            "dna_name": Optional[str],
            "similarity": float (0.0 to 1.0),
            "matched_steps": List[str]
        }
        """
        history = account_history or []
        events_observed = set()

        # 1. Detect observed behavioural steps in current transaction
        if features.get("is_new_device", 0.0) == 1.0:
            events_observed.add("NEW_DEVICE")

        if features.get("is_new_beneficiary", 0.0) == 1.0:
            events_observed.add("NEW_BENEFICIARY")

        if features.get("is_unusual_hour", 0.0) == 1.0:
            events_observed.add("UNUSUAL_HOURS")

        amt = float(current_txn.get("amount", 0.0))
        if amt <= 100.0:
            events_observed.add("MICRO_PROBE")
        elif amt >= 40000.0:
            events_observed.add("LARGE_TRANSFER")
            if amt >= 90000.0:
                events_observed.add("MAX_LIMIT_TRANSFER")

        # Round numbers e.g. 50000, 25000 are typical in mule transfers
        if amt >= 5000.0 and amt % 1000 == 0:
            events_observed.add("ROUND_AMOUNT_DRAIN")

        # 2. Inspect recent historical transactions (last 30 minutes)
        txn_time = current_txn.get("timestamp")
        if isinstance(txn_time, str):
            txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00"))
        elif not txn_time:
            txn_time = datetime.now(timezone.utc)

        recent_txns = [
            t for t in history
            if (t.get("timestamp") if isinstance(t.get("timestamp"), datetime) else datetime.fromisoformat(str(t.get("timestamp")).replace("Z", "+00:00"))) >= (txn_time - timedelta(minutes=30))
        ]

        if len(recent_txns) >= 3:
            events_observed.add("BURST_VELOCITY")

        recent_beneficiaries = {str(t.get("beneficiary_id", "")).strip().lower() for t in recent_txns if t.get("beneficiary_id")}
        if len(recent_beneficiaries) >= 3:
            events_observed.add("MULTIPLE_BENEFICIARIES")

        # Check if a micro-probe occurred in the recent past preceding this large transfer
        has_recent_probe = any(float(t.get("amount", 0.0)) <= 100.0 for t in recent_txns)
        if has_recent_probe and amt >= 30000.0:
            events_observed.add("MICRO_PROBE")
            events_observed.add("LARGE_TRANSFER")

        # 3. Compare with known templates
        best_match = None
        highest_similarity = 0.0

        for tmpl in KNOWN_ATTACK_DNA_TEMPLATES:
            required_steps = tmpl["steps"]
            matched_count = sum(1 for step in required_steps if step in events_observed)
            similarity = matched_count / float(len(required_steps))

            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = {
                    "matched": similarity >= 0.70,
                    "dna_id": tmpl["dna_id"],
                    "dna_name": tmpl["name"],
                    "description": tmpl["description"],
                    "similarity": round(similarity, 4),
                    "severity": tmpl["severity"],
                    "matched_steps": [s for s in required_steps if s in events_observed]
                }

        if best_match and best_match["matched"]:
            return best_match

        return {
            "matched": False,
            "dna_id": None,
            "dna_name": None,
            "description": None,
            "similarity": round(highest_similarity, 4),
            "severity": 0.0,
            "matched_steps": list(events_observed)
        }

