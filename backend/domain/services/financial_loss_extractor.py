import re
from typing import Optional

def extract_financial_loss(text: Optional[str]) -> Optional[float]:
    """
    Deterministically extracts reported financial loss from scam narratives,
    bank escalation messages, and citizen cybercrime complaints.
    
    Supports:
    - Standard currency codes: INR 95,000.00, Rs. 45,000, Rs 5000, ₹75,000, Rs.1,50,000
    - Multiplier keywords: 'Lakh', 'Lakhs', 'Lac', 'Lacs' (x100,000), 'Crore', 'Cr' (x10,000,000), 'k', 'thousand' (x1,000)
    - Action-oriented phrases: 'transferred INR 95,000', 'lost Rs. 50,000', 'debited ₹12,500'
    """
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip()
    if not cleaned:
        return None

    found_amounts = []

    # Pattern 1: Action verbs followed by or preceding currency symbols and amounts
    # e.g., "transferred INR 95,000.00", "debited Rs. 50,000", "lost ₹1,25,000", "loss of INR 20000"
    action_pattern = re.compile(
        r'(?:transferred|transfer|paid|lost|loss\s+of|debited|defrauded\s+of|scammed\s+for|amount\s+of|sent|paid\s+sum\s+of)\s+'
        r'(?:INR|Rs\.?|₹|rupees)?\s*'
        r'([\d,]+(?:\.\d{1,2})?)\s*'
        r'(?:lakhs?|lacs?|crores?|cr|k|thousand)?',
        re.IGNORECASE
    )

    # Pattern 2: Currency symbol prefixed amounts: INR 95,000.00, ₹ 50,000, Rs. 1,00,000
    currency_prefix_pattern = re.compile(
        r'(?:INR|Rs\.?|₹|rupees)\s*'
        r'([\d,]+(?:\.\d{1,2})?)\s*'
        r'(lakhs?|lacs?|crores?|cr|k|thousand)?',
        re.IGNORECASE
    )

    # Pattern 3: Quantities with explicit magnitude suffixes: "2.5 lakhs", "1.2 crore", "50k"
    magnitude_pattern = re.compile(
        r'(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|cr|k|thousand)\b',
        re.IGNORECASE
    )

    def parse_numeric(val_str: str) -> Optional[float]:
        try:
            clean_val = val_str.replace(',', '').strip()
            return float(clean_val)
        except (ValueError, TypeError):
            return None

    def apply_multiplier(num: float, unit: Optional[str]) -> float:
        if not unit:
            return num
        unit_lower = unit.lower().strip()
        if unit_lower in ['lakh', 'lakhs', 'lac', 'lacs']:
            return num * 100_000.0
        elif unit_lower in ['crore', 'crores', 'cr']:
            return num * 10_000_000.0
        elif unit_lower in ['k', 'thousand']:
            return num * 1_000.0
        return num

    # 1. Check action-oriented matches first (highest confidence)
    for match in action_pattern.finditer(cleaned):
        raw_num = match.group(1)
        # Check if there is a unit immediately following the match
        matched_str = match.group(0).lower()
        multiplier = None
        for u in ['lakhs', 'lakh', 'lacs', 'lac', 'crores', 'crore', 'cr', 'thousand', 'k']:
            if u in matched_str:
                multiplier = u
                break
        parsed = parse_numeric(raw_num)
        if parsed is not None and parsed > 0:
            val = apply_multiplier(parsed, multiplier)
            # Avoid single digit or small anomaly numbers from action matches
            if val >= 10.0:
                found_amounts.append(val)

    # 2. Check currency prefixed matches
    for match in currency_prefix_pattern.finditer(cleaned):
        raw_num = match.group(1)
        unit = match.group(2)
        parsed = parse_numeric(raw_num)
        if parsed is not None and parsed > 0:
            val = apply_multiplier(parsed, unit)
            # Exclude 10-digit or 12-digit numbers that are likely phone or aadhaar/bank accounts
            raw_digits = raw_num.replace(',', '').split('.')[0]
            if len(raw_digits) in (10, 11, 12) and not unit:
                continue
            if val >= 10.0:
                found_amounts.append(val)

    # 3. Check magnitude pattern
    for match in magnitude_pattern.finditer(cleaned):
        raw_num = match.group(1)
        unit = match.group(2)
        parsed = parse_numeric(raw_num)
        if parsed is not None and parsed > 0:
            val = apply_multiplier(parsed, unit)
            if val >= 1000.0:
                found_amounts.append(val)

    if not found_amounts:
        return None

    # Filter out potential years (e.g., 2024, 2025, 2026) if they appear without currency
    valid_amounts = [a for a in found_amounts if not (1990 <= a <= 2030 and a.is_integer() and a not in [2000.0])]

    if not valid_amounts:
        return None

    # Return the maximum plausible loss amount mentioned
    return max(valid_amounts)
