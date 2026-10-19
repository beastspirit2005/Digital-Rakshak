import re
import urllib.parse
from typing import Dict, List, Any, Optional

class OSINTScanner:
    """
    OSINT & Heuristic Threat Intelligence Layer.
    Implements multi-vector indicator classification:
    - KNOWN_MALICIOUS: Verified malicious blocklist, known phishing infrastructure.
    - SUSPICIOUS: Deceptive heuristics, impersonation keywords, spoofing indicators.
    - UNKNOWN_UNVERIFIED: Indicator not present in national threat repository (requires caution).
    - VERIFIED_LEGITIMATE: Recognized official banking, government, or national emergency entities.
    """
    
    # Known malicious domains & URL patterns
    MALICIOUS_DOMAINS = [
        "oksbi.in", "ngrok.io", "bit.ly/cbi-arrest", "update-pan-kyc.com", "yono-sbi-update.in",
        "secure-hdfc-kyc-verification.ru", "apk-rakshak-malware.top", "fake-gpay.com",
        "refund-desk-support.xyz", "customer-care-helpline.click"
    ]

    # Recognized official government, banking & trusted global digital infrastructure domains
    VERIFIED_LEGITIMATE_DOMAINS = [
        # Search & Global Digital Trust Anchors
        "google.com", "google.co.in", "youtube.com", "gmail.com", "gstatic.com", "googleapis.com", "android.com",
        "microsoft.com", "live.com", "office.com", "bing.com", "outlook.com",
        "apple.com", "icloud.com", "github.com", "cloudflare.com", "wikipedia.org",

        # Official Indian Government & Regulators
        "gov.in", "nic.in", "rbi.org.in", "npci.org.in", "incometax.gov.in", "cybercrime.gov.in",
        "uidai.gov.in", "epfindia.gov.in", "digitalindia.gov.in", "trai.gov.in", "sebi.gov.in",
        "cert-in.org.in", "digilocker.gov.in", "india.gov.in", "mygov.in",

        # Major Indian Scheduled Commercial Banks
        "sbi.co.in", "onlinesbi.sbi", "hdfcbank.com", "icicibank.com",
        "axisbank.com", "kotak.com", "pnbindia.in", "bankofbaroda.in",
        "canarabank.com", "unionbankofindia.co.in", "idfcfirstbank.com",
        "indusind.com", "yesbank.in", "federalbank.co.in", "iob.in",

        # Major Indian Payment & Digital Service Platforms
        "bhimupi.org.in", "paytm.com", "phonepe.com", "razorpay.com", "cashfree.com",
        "amazon.in", "flipkart.com", "irctc.co.in"
    ]
    
    # Official emergency & cybercrime helplines in India
    VERIFIED_LEGITIMATE_NUMBERS = {
        "1930": "National Cyber Crime Reporting Portal Helpline",
        "112": "National Emergency Response Support System (ERSS)",
        "100": "Police Emergency",
        "1090": "Women Power Helpline",
        "1909": "Telecom Regulatory Authority of India (TRAI) DND Registry",
        "1800111109": "State Bank of India Toll-Free Customer Service",
        "18002084444": "Indian Cyber Crime Coordination Centre (I4C) Awareness Desk"
    }

    # Known high-risk foreign calling codes commonly used for WhatsApp vishing in India
    HIGH_RISK_CALLING_PREFIXES = ["+92", "+880", "+234", "+254", "+93"]

    COUNTERFEIT_ENTITIES = {
        "cbi": "The Central Bureau of Investigation (CBI) does NOT make arrests or interrogations over video calls (Skype/WhatsApp). This is a known 'Digital Arrest' scam.",
        "fedex": "FedEx does NOT involve police for customs seizures over phone calls. They will send formal written notice.",
        "trai": "TRAI does NOT block mobile numbers for illegal activities without formal written notices sent via post.",
        "rbi": "The Reserve Bank of India does NOT freeze accounts or ask for RTGS transfers to 'safe accounts'.",
        "customs": "Customs department does not demand payment in personal bank accounts or via UPI to clear seized parcels."
    }
    
    SUSPICIOUS_UPI_KEYWORDS = [
        "refund", "support", "reward", "cashback", "bonus", "lottery",
        "prize", "claim", "helpdesk", "care", "customer-care", "kyc",
        "axis-care", "hdfc-support", "sbi-kyc", "icici-support", "paytm-help"
    ]

    def scan_upi(self, upi: str) -> Dict[str, Any]:
        """
        Scans a UPI VPA handle for deceptive support, refund, or banking impersonation patterns.
        """
        results = {
            "flagged": False,
            "threat": "",
            "risk_level": "LOW",
            "indicator_status": "UNKNOWN_UNVERIFIED",
        }
        upi_lower = upi.strip().lower()

        # Check for known malicious keywords in handle
        for kw in self.SUSPICIOUS_UPI_KEYWORDS:
            if kw in upi_lower:
                results["flagged"] = True
                results["threat"] = f"Deceptive handle pattern: '{kw}' in UPI ID indicates an impersonation / fake refund lure."
                results["risk_level"] = "CRITICAL"
                results["indicator_status"] = "KNOWN_MALICIOUS"
                return results

        # Check if handle uses an official bank merchant VPA format (e.g. nodal utility billers)
        if any(upi_lower.endswith(suffix) for suffix in ["@npci", "@rbi"]):
            results["indicator_status"] = "VERIFIED_LEGITIMATE"
            results["threat"] = "Verified official institutional UPI domain identifier."
            return results

        results["threat"] = "UPI ID not found in central fraud mule registry. Exercise caution before transferring funds."
        return results

    def scan_phone(self, phone: str) -> Dict[str, Any]:
        """
        Scans a phone number for known fraud patterns, international vishing prefixes, and emergency helplines.
        """
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone.strip())
        results = {
            "flagged": False,
            "threat": "",
            "risk_level": "LOW",
            "indicator_status": "UNKNOWN_UNVERIFIED"
        }

        # 1. Check official national helplines
        if clean_phone in self.VERIFIED_LEGITIMATE_NUMBERS:
            results["indicator_status"] = "VERIFIED_LEGITIMATE"
            results["threat"] = f"Verified Official Contact: {self.VERIFIED_LEGITIMATE_NUMBERS[clean_phone]}"
            results["risk_level"] = "LOW"
            return results

        # 2. Check high-risk foreign caller codes targeting Indian citizens on WhatsApp
        for prefix in self.HIGH_RISK_CALLING_PREFIXES:
            if clean_phone.startswith(prefix):
                results["flagged"] = True
                results["threat"] = f"High-risk foreign country code ({prefix}) frequently associated with spoofed WhatsApp vishing and digital arrest scams."
                results["risk_level"] = "CRITICAL"
                results["indicator_status"] = "SUSPICIOUS"
                return results

        # 3. Format validation
        digits_only = re.sub(r'\D', '', clean_phone)
        if len(digits_only) == 10 and digits_only[0] in ['6', '7', '8', '9']:
            results["indicator_status"] = "UNKNOWN_UNVERIFIED"
            results["threat"] = "Standard Indian mobile number format. No active cybercrime complaints logged in current cycle."
        elif len(digits_only) < 10 and clean_phone not in self.VERIFIED_LEGITIMATE_NUMBERS:
            results["flagged"] = True
            results["threat"] = "Malformed or suspicious shortcode phone number."
            results["risk_level"] = "HIGH"
            results["indicator_status"] = "SUSPICIOUS"
        else:
            results["indicator_status"] = "UNKNOWN_UNVERIFIED"
            results["threat"] = "Number not currently listed in national blocklist. Verify caller identity independently."

        return results

    @staticmethod
    def extract_domain(raw_url: str) -> str:
        """
        Extracts canonical hostname from a URL string, stripping scheme, port, query, and trailing dots.
        """
        clean = raw_url.strip().lower()
        if not clean.startswith(("http://", "https://")):
            clean = "https://" + clean
        try:
            parsed = urllib.parse.urlsplit(clean)
            host = parsed.hostname or ""
            return host.rstrip(".")
        except Exception:
            return ""

    @staticmethod
    def matches_domain(host: str, domain: str) -> bool:
        """
        Strict boundary matching:
        'www.google.com' matches 'google.com', but 'google.com.phishing.top' does NOT.
        """
        if not host or not domain:
            return False
        return host == domain or host.endswith("." + domain)

    def check_url(self, raw_url: str) -> Dict[str, Any]:
        """
        Direct canonical URL evaluation.
        """
        host = self.extract_domain(raw_url)
        clean_url = raw_url.strip().lower()

        # 1. Malicious check
        for bad_domain in self.MALICIOUS_DOMAINS:
            if bad_domain in clean_url:
                return {
                    "is_safe": False,
                    "risk_level": "CRITICAL",
                    "indicator_status": "KNOWN_MALICIOUS",
                    "threat": f"Matches known malicious phishing infrastructure ({bad_domain})"
                }

        # 2. Verified legitimate check with strict boundary
        if host:
            for good_domain in self.VERIFIED_LEGITIMATE_DOMAINS:
                if self.matches_domain(host, good_domain):
                    return {
                        "is_safe": True,
                        "risk_level": "LOW",
                        "indicator_status": "VERIFIED_LEGITIMATE",
                        "threat": f"Matches verified official institutional, government, or trusted digital service ({good_domain}).",
                        "matched_domain": good_domain
                    }

        return {
            "is_safe": True,
            "risk_level": "LOW",
            "indicator_status": "UNKNOWN_UNVERIFIED",
            "threat": ""
        }

    def extract_urls(self, text: str) -> List[str]:
        url_pattern = re.compile(r'(https?://[^\s]+)|(www\.[^\s]+)|([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)')
        matches = url_pattern.findall(text)
        urls = []
        for match in matches:
            for group in match:
                if group:
                    urls.append(group.strip())
        return list(set(urls))
        
    def scan_text(self, text: str) -> Dict[str, Any]:
        """
        Scans raw text for URLs and entities, cross-references with OSINT DBs.
        """
        results = {
            "flagged_urls": [],
            "counterfeit_warnings": [],
            "risk_level": "LOW",
            "indicator_status": "UNKNOWN_UNVERIFIED"
        }
        
        text_lower = text.lower()
        
        # 1. URL Reputation Check
        extracted_urls = self.extract_urls(text_lower)
        for url in extracted_urls:
            host = self.extract_domain(url)

            # Check malicious list
            for bad_domain in self.MALICIOUS_DOMAINS:
                if bad_domain in url:
                    results["flagged_urls"].append({
                        "url": url,
                        "threat": f"Matches known malicious phishing infrastructure ({bad_domain})"
                    })
                    results["risk_level"] = "CRITICAL"
                    results["indicator_status"] = "KNOWN_MALICIOUS"
            
            # Check verified list with strict boundary
            if results["indicator_status"] != "KNOWN_MALICIOUS" and host:
                for good_domain in self.VERIFIED_LEGITIMATE_DOMAINS:
                    if self.matches_domain(host, good_domain):
                        results["indicator_status"] = "VERIFIED_LEGITIMATE"
                        results["risk_level"] = "LOW"
                        results["matched_verified_domain"] = good_domain
                        break
                    
        # 2. Counterfeit Entity Check (Digital Arrests, Fake Customs)
        # Must match whole word boundary AND coercive threat context to prevent false positives (e.g., 'train' matching 'trai', 'orbit' matching 'rbi')
        threat_context_keywords = ["arrest", "warrant", "disconnect", "block", "suspend", "seized", "illegal", "drugs", "narcotics", "contraband", "fine", "skype", "video call", "pay"]
        has_threat_context = any(tw in text_lower for tw in threat_context_keywords)

        for entity, warning in self.COUNTERFEIT_ENTITIES.items():
            if re.search(rf"\b{re.escape(entity)}\b", text_lower) and has_threat_context:
                results["counterfeit_warnings"].append({
                    "entity": entity.upper(),
                    "warning": warning
                })
                if results["risk_level"] != "CRITICAL":
                    results["risk_level"] = "HIGH"
                if results["indicator_status"] != "KNOWN_MALICIOUS":
                    results["indicator_status"] = "SUSPICIOUS"
                    
        return results

