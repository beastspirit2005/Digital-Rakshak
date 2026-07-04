import re
from typing import Dict, List, Any

class OSINTScanner:
    """
    Mock OSINT Enrichment Layer.
    In a production environment, this would call VirusTotal, RiskIQ, or custom OSINT APIs.
    For this prototype, it uses deterministic heuristic rules to flag known counterfeit
    entities and malicious URLs.
    """
    
    # Mock databases
    MALICIOUS_DOMAINS = [
        "oksbi.in", "ngrok.io", "bit.ly/cbi-arrest", "update-pan-kyc.com", "yono-sbi-update.in"
    ]
    
    COUNTERFEIT_ENTITIES = {
        "cbi": "The Central Bureau of Investigation (CBI) does NOT make arrests over video calls (Skype/WhatsApp). This is a known 'Digital Arrest' scam.",
        "fedex": "FedEx does NOT involve police for customs seizures over phone calls. They will send formal written notice.",
        "trai": "TRAI does NOT block mobile numbers for illegal activities without formal written notices sent via post.",
        "rbi": "The Reserve Bank of India does NOT freeze accounts or ask for RTGS transfers to 'safe accounts'."
    }
    
    def extract_urls(self, text: str) -> List[str]:
        # Simple regex for finding domains/URLs
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
        Scans raw text for URLs and entities, cross-references with mock OSINT DBs.
        """
        results = {
            "flagged_urls": [],
            "counterfeit_warnings": [],
            "risk_level": "LOW"
        }
        
        text_lower = text.lower()
        
        # 1. URL Reputation Check
        extracted_urls = self.extract_urls(text_lower)
        for url in extracted_urls:
            for bad_domain in self.MALICIOUS_DOMAINS:
                if bad_domain in url:
                    results["flagged_urls"].append({
                        "url": url,
                        "threat": f"Matches known malicious phishing infrastructure ({bad_domain})"
                    })
                    results["risk_level"] = "CRITICAL"
                    
        # 2. Counterfeit Entity Check (Digital Arrests, Fake Customs)
        for entity, warning in self.COUNTERFEIT_ENTITIES.items():
            if entity in text_lower:
                results["counterfeit_warnings"].append({
                    "entity": entity.upper(),
                    "warning": warning
                })
                # Escalate risk if counterfeit authority is invoked
                if results["risk_level"] != "CRITICAL":
                    results["risk_level"] = "HIGH"
                    
        return results
