from typing import Dict, Any, List

class UrgencyEngine:
    """
    Independent Urgency & Triage Evaluation Engine for Digital Rakshak Investigator Connect.
    Core Rule: Evaluates threat strictly based on active harm, threat velocity, and potential impact.
    Subscription plan is deliberately NEVER considered in urgency evaluation.
    """

    CRITICAL_INCIDENT_TYPES = {
        "digital_arrest",
        "banking_fraud",
        "upi_fraud",
        "loan_extortion",
        "extortion",
        "sim_swap"
    }

    @classmethod
    def evaluate(
        cls,
        incident_type: str,
        is_ongoing: bool,
        hours_since_incident: float = 0.0,
        estimated_loss_inr: float = 0.0,
        has_compromised_credentials: bool = False
    ) -> Dict[str, Any]:
        """
        Determines the operational urgency level and relevant immediate containment instructions.
        Levels: 'critical', 'high', 'standard'.
        """
        incident_clean = (incident_type or "").lower().strip()
        urgency = "standard"
        reasons: List[str] = []

        # 1. Critical Tier Check
        if is_ongoing:
            urgency = "critical"
            reasons.append("Active ongoing fraud or threat in progress.")
        elif hours_since_incident <= 2.0 and incident_clean in cls.CRITICAL_INCIDENT_TYPES:
            urgency = "critical"
            reasons.append(f"Recent {incident_clean.replace('_', ' ').title()} within the golden 2-hour window.")

        # 2. High Tier Check
        elif hours_since_incident <= 48.0:
            urgency = "high"
            reasons.append("Incident occurred within the past 48 hours.")
        elif estimated_loss_inr >= 50000.0:
            urgency = "high"
            reasons.append(f"High financial impact (₹{estimated_loss_inr:,.2f}).")
        elif has_compromised_credentials:
            urgency = "high"
            reasons.append("Account authentication credentials or OTP exposed.")
        else:
            urgency = "standard"
            reasons.append("Historical incident or general inquiry.")

        # Emergency containment guidance
        guidance = cls.get_emergency_guidance(urgency, incident_clean)

        return {
            "urgency_level": urgency,
            "reasons": reasons,
            "emergency_guidance": guidance
        }

    @classmethod
    def get_emergency_guidance(cls, urgency: str, incident_type: str) -> List[Dict[str, str]]:
        actions = [
            {
                "title": "Call National Cybercrime Helpline 1930",
                "description": "If financial loss has occurred, dial 1930 immediately to freeze fraudulent transaction accounts within the inter-bank golden hour.",
                "action_type": "call",
                "action_target": "tel:1930",
                "is_urgent": True
            },
            {
                "title": "File on cybercrime.gov.in",
                "description": "Log your formal complaint on the Ministry of Home Affairs National Cyber Crime Reporting Portal.",
                "action_type": "link",
                "action_target": "https://cybercrime.gov.in/",
                "is_urgent": False
            }
        ]

        if incident_type in ["banking_fraud", "upi_fraud", "sim_swap"]:
            actions.insert(0, {
                "title": "Block Bank Account & UPI ID",
                "description": "Contact your bank's toll-free customer care immediately to block debit cards, net banking, and UPI access.",
                "action_type": "checklist",
                "action_target": "",
                "is_urgent": True
            })

        if incident_type == "digital_arrest":
            actions.insert(0, {
                "title": "Disconnect Video Call / Threatening Calls",
                "description": "Indian Police, CBI, ED, and Supreme Court NEVER conduct digital arrests via Skype, WhatsApp, or video call. Disconnect immediately.",
                "action_type": "warning",
                "action_target": "",
                "is_urgent": True
            })

        return actions
