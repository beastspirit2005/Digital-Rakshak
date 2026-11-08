import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from domain.services.financial_loss_extractor import extract_financial_loss
from domain.models.bank import TransactionVerificationStatus


class ExtractedTransactionIntelligence(BaseModel):
    transaction_reference: Optional[str] = Field(None, description="Extracted UTR or RRN 12-digit reference")
    amount: Optional[float] = Field(None, description="Extracted financial loss amount in INR")
    payment_rail: str = Field("UPI", description="Inferred payment rail: UPI, IMPS, NEFT, RTGS, CARD")
    
    # Remitter / Victim details
    remitter_ifsc: Optional[str] = Field(None, description="Extracted victim bank IFSC")
    remitter_vpa: Optional[str] = Field(None, description="Extracted victim UPI VPA")
    remitter_account_masked: Optional[str] = Field(None, description="Masked victim account number")
    remitter_bank_hint: Optional[str] = Field(None, description="Extracted victim bank name keyword")

    # Beneficiary / Suspect details
    beneficiary_ifsc: Optional[str] = Field(None, description="Extracted suspect bank IFSC")
    beneficiary_vpa: Optional[str] = Field(None, description="Extracted suspect UPI VPA")
    beneficiary_account_masked: Optional[str] = Field(None, description="Masked suspect account number")
    beneficiary_bank_hint: Optional[str] = Field(None, description="Extracted suspect bank name keyword")

    verification_status: str = Field(TransactionVerificationStatus.EXTRACTED_UNVERIFIED.value)
    confidence_score: float = Field(0.0, description="Extraction confidence score from 0.0 to 1.0")
    extraction_notes: List[str] = Field(default_factory=list)


# Regex patterns
IFSC_REGEX = re.compile(r'\b([A-Z]{4}0[A-Z0-9]{6})\b')
VPA_REGEX = re.compile(r'\b([a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9.\-_]{2,})\b')

# 12-digit UTR/RRN pattern (often prefixed by UTR, RRN, Ref, Txn ID, or standing alone near payment verbs)
UTR_EXPLICIT_REGEX = re.compile(
    r'(?:UTR|RRN|Ref(?:erence)?(?:\s*No\.?)?|Txn(?:\s*ID)?|Transaction(?:\s*ID)?|Reference)\s*[:=\-#]?\s*([0-9]{12})\b',
    re.IGNORECASE
)
STANDALONE_12DIGIT_REGEX = re.compile(r'\b([0-9]{12})\b')

# Account number pattern: 9 to 18 digits near account keywords
ACCOUNT_NEAR_KEYWORD_REGEX = re.compile(
    r'(?:a/c|acct|account(?:\s*number|\s*no\.?)?)\s*[:=\-#]?\s*(?:X{2,}|[*]{2,})?([0-9]{4,18})\b',
    re.IGNORECASE
)

# Common Indian Bank names for text hinting
BANK_NAME_KEYWORDS = {
    "sbi": "SBIN",
    "state bank": "SBIN",
    "hdfc": "HDFC",
    "icici": "ICIC",
    "axis": "AXIS",
    "pnb": "PUNB",
    "punjab national": "PUNB",
    "bank of baroda": "BARB",
    "bob": "BARB",
    "canara": "CNRB",
    "union bank": "UBIN",
    "kotak": "KKBK",
    "idfc": "IDFB",
    "yes bank": "YESB",
    "indusind": "INDB",
    "paytm": "PYTM",
    "airtel payment": "AIRP",
    "india post": "IPOS",
}


def mask_account_number(acc: str) -> str:
    """Masks all but the last 4 digits of a bank account number."""
    clean = re.sub(r'[\s\-]', '', acc)
    if len(clean) <= 4:
        return f"****{clean}"
    return f"{'*' * (len(clean) - 4)}{clean[-4:]}"


def extract_transaction_intelligence(text: Optional[str]) -> ExtractedTransactionIntelligence:
    """
    Parses unstructured citizen complaints, bank switch logs, and investigator notes
    to extract, validate, and structure financial transaction metadata.
    """
    if not text or not isinstance(text, str):
        return ExtractedTransactionIntelligence()

    raw = text.strip()
    notes: List[str] = []
    confidence = 0.3

    # 1. Extract Reported Loss
    amount = extract_financial_loss(raw)
    if amount and amount > 0:
        confidence += 0.2
        notes.append(f"Reported loss identified: ₹{amount:,.2f}")

    # 2. Extract UTR / RRN
    txn_ref = None
    explicit_utr = UTR_EXPLICIT_REGEX.search(raw)
    if explicit_utr:
        txn_ref = explicit_utr.group(1)
        confidence += 0.25
        notes.append(f"Explicit UTR/RRN reference: {txn_ref}")
    else:
        # Check for 12-digit number (excluding 12-digit Aadhaar / phone numbers)
        candidates = STANDALONE_12DIGIT_REGEX.findall(raw)
        # Filter candidates that aren't phone numbers (often 10 digits)
        for cand in candidates:
            # Typical Indian UTR starts with digit or year, avoid 91xxxxxxxxxx phone numbers
            if not cand.startswith("91") and not cand.startswith("00"):
                txn_ref = cand
                confidence += 0.15
                notes.append(f"Plausible 12-digit UTR/RRN: {txn_ref}")
                break

    # 3. Extract IFSC Codes
    ifsc_matches = IFSC_REGEX.findall(raw)
    remitter_ifsc = None
    beneficiary_ifsc = None

    if len(ifsc_matches) == 1:
        # Check context: is it sender or beneficiary?
        match_pos = raw.find(ifsc_matches[0])
        preceding = raw[max(0, match_pos - 60):match_pos].lower()
        if any(w in preceding for w in ["to", "beneficiary", "credited to", "sent to", "fraudster"]):
            beneficiary_ifsc = ifsc_matches[0]
            notes.append(f"Beneficiary IFSC identified: {beneficiary_ifsc}")
        elif any(w in preceding for w in ["from", "my account", "debited from", "remitter"]):
            remitter_ifsc = ifsc_matches[0]
            notes.append(f"Remitter IFSC identified: {remitter_ifsc}")
        else:
            # Default single IFSC in a complaint is almost always the beneficiary/fraudster account
            beneficiary_ifsc = ifsc_matches[0]
            notes.append(f"IFSC resolved as suspect beneficiary: {beneficiary_ifsc}")
        confidence += 0.2
    elif len(ifsc_matches) >= 2:
        remitter_ifsc = ifsc_matches[0]
        beneficiary_ifsc = ifsc_matches[1]
        notes.append(f"Dual IFSCs extracted: Remitter={remitter_ifsc}, Beneficiary={beneficiary_ifsc}")
        confidence += 0.3

    # 4. Extract UPI VPAs
    vpa_matches = VPA_REGEX.findall(raw)
    remitter_vpa = None
    beneficiary_vpa = None

    # Filter out email addresses that aren't banking handles
    valid_vpas = [
        v for v in vpa_matches 
        if not v.lower().endswith(('.com', '.org', '.net', '.in', '.gov', '.edu')) 
        or any(h in v.lower() for h in ['okhdfcbank', 'okaxis', 'okicici', 'oksbi', 'ybl', 'paytm', 'airtel'])
    ]

    if len(valid_vpas) == 1:
        beneficiary_vpa = valid_vpas[0]
        notes.append(f"Beneficiary UPI VPA identified: {beneficiary_vpa}")
        confidence += 0.25
    elif len(valid_vpas) >= 2:
        remitter_vpa = valid_vpas[0]
        beneficiary_vpa = valid_vpas[1]
        notes.append(f"Dual VPAs extracted: Remitter={remitter_vpa}, Beneficiary={beneficiary_vpa}")
        confidence += 0.3

    # 5. Extract Account Numbers
    account_matches = ACCOUNT_NEAR_KEYWORD_REGEX.findall(raw)
    remitter_acc = None
    beneficiary_acc = None

    if len(account_matches) == 1:
        # Check context
        beneficiary_acc = mask_account_number(account_matches[0])
        notes.append(f"Beneficiary account identified: {beneficiary_acc}")
        confidence += 0.15
    elif len(account_matches) >= 2:
        remitter_acc = mask_account_number(account_matches[0])
        beneficiary_acc = mask_account_number(account_matches[1])
        notes.append(f"Accounts identified: Remitter={remitter_acc}, Beneficiary={beneficiary_acc}")
        confidence += 0.25

    # 6. Extract Bank Name Keywords
    remitter_bank_hint = None
    beneficiary_bank_hint = None
    raw_lower = raw.lower()

    for kw, bank_code in BANK_NAME_KEYWORDS.items():
        if kw in raw_lower:
            # Check if it precedes/succeeds 'my' or 'from'
            pos = raw_lower.find(kw)
            context = raw_lower[max(0, pos - 40):min(len(raw_lower), pos + 40)]
            if any(w in context for w in ["my", "from", "mine", "debited"]):
                if not remitter_bank_hint:
                    remitter_bank_hint = bank_code
            elif any(w in context for w in ["to", "into", "beneficiary", "credited", "fraudster"]):
                if not beneficiary_bank_hint:
                    beneficiary_bank_hint = bank_code
            else:
                if not beneficiary_bank_hint:
                    beneficiary_bank_hint = bank_code

    # 7. Infer Payment Rail
    payment_rail = "UPI"
    if "neft" in raw_lower:
        payment_rail = "NEFT"
    elif "rtgs" in raw_lower:
        payment_rail = "RTGS"
    elif "imps" in raw_lower:
        payment_rail = "IMPS"
    elif "card" in raw_lower or "credit card" in raw_lower or "debit card" in raw_lower:
        payment_rail = "CARD"
    elif beneficiary_ifsc and not beneficiary_vpa:
        payment_rail = "IMPS"

    # Normalize confidence to [0.0, 1.0]
    final_confidence = min(1.0, round(confidence, 2))
    
    # Set verification state
    verification_status = TransactionVerificationStatus.EXTRACTED_UNVERIFIED.value
    if txn_ref and (beneficiary_ifsc or beneficiary_vpa):
        verification_status = TransactionVerificationStatus.RESOLVED_INFERRED.value

    return ExtractedTransactionIntelligence(
        transaction_reference=txn_ref,
        amount=amount,
        payment_rail=payment_rail,
        remitter_ifsc=remitter_ifsc,
        remitter_vpa=remitter_vpa,
        remitter_account_masked=remitter_acc,
        remitter_bank_hint=remitter_bank_hint,
        beneficiary_ifsc=beneficiary_ifsc,
        beneficiary_vpa=beneficiary_vpa,
        beneficiary_account_masked=beneficiary_acc,
        beneficiary_bank_hint=beneficiary_bank_hint,
        verification_status=verification_status,
        confidence_score=final_confidence,
        extraction_notes=notes
    )
