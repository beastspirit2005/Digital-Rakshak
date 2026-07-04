import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from domain.models.scam_pattern import ScamPattern
from infrastructure.graph.neo4j_client import IntelligenceGraph

logger = logging.getLogger(__name__)

# Simulated OSINT Database
MOCK_OSINT_FEEDS = [
    {
        "scam_type": "DIGITAL_ARREST",
        "source": "MHA_CYBER_FEED",
        "indicators": {
            "phone_numbers": ["+919876543210", "+919988776655"],
            "upi_ids": ["cbi.official@sbi", "cybercell@icici"]
        },
        "raw_text_example": "This is a call from CBI. Your Aadhaar card has been used in a money laundering case. Do not disconnect the call. Transfer funds to secret RBI account for verification.",
        "modus_operandi": "Scammers impersonate police or CBI, claiming a parcel or Aadhaar card is linked to money laundering. They demand transfer of funds to 'safe' accounts via UPI or NEFT."
    },
    {
        "scam_type": "FEDEX_SCAM",
        "source": "GLOBAL_PHISH_DB",
        "indicators": {
            "phone_numbers": ["+918877665544"],
            "urls": ["fedex-tracking-urgent.com"]
        },
        "raw_text_example": "Your FedEx parcel containing illegal items has been detained by Customs. Press 1 to speak to Customs officer or face arrest.",
        "modus_operandi": "Victims receive automated IVR calls claiming a parcel in their name contains drugs/passports. Fake customs officers demand bribes or 'fines' via crypto or UPI."
    },
    {
        "scam_type": "ELECTRICITY_BOARD",
        "source": "TRAI_DND_REGISTRY",
        "indicators": {
            "phone_numbers": ["+917766554433", "+916655443322"]
        },
        "raw_text_example": "Dear consumer, your electricity power will be disconnected tonight at 9:30 PM from the electricity office. Because your previous month bill was not updated. Please immediately contact with our electricity officer 9876543210. Thank you.",
        "modus_operandi": "SMS sent en-masse threatening immediate power cut. When victim calls, they are asked to download a remote access app (AnyDesk/TeamViewer) to 'pay a 10 Rs update fee', resulting in total bank drain."
    }
]

class OSINTConnector:
    """
    Simulated OSINT Connector that fetches known global threat intelligence
    and syncs it into our Postgres (RAG examples) and Neo4j (Graph flags).
    """
    
    async def sync_public_feeds(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Pulls the latest threat intelligence and stores it.
        """
        logger.info("Starting OSINT feed sync...")
        
        # 1. Sync to Postgres (for RAG/Few-Shot Learning)
        synced_patterns = 0
        for feed in MOCK_OSINT_FEEDS:
            # Check if exists (simple check by raw_text_example for mock)
            from sqlalchemy import select
            result = await db.execute(select(ScamPattern).where(ScamPattern.raw_text_example == feed["raw_text_example"]))
            existing = result.scalar_one_or_none()
            
            if not existing:
                new_pattern = ScamPattern(
                    scam_type=feed["scam_type"],
                    source=feed["source"],
                    raw_text_example=feed["raw_text_example"],
                    modus_operandi=feed["modus_operandi"],
                    indicators_of_compromise=feed["indicators"]
                )
                db.add(new_pattern)
                synced_patterns += 1
                
        await db.commit()
        
        # 2. Sync to Neo4j (for Graph Clustering & OSINT Flags)
        synced_iocs = 0
        graph = IntelligenceGraph()
        try:
            for feed in MOCK_OSINT_FEEDS:
                indicators = feed["indicators"]
                for phone in indicators.get("phone_numbers", []):
                    await graph.add_osint_entity("PhoneNumber", phone, feed["source"], feed["scam_type"])
                    synced_iocs += 1
                for upi in indicators.get("upi_ids", []):
                    await graph.add_osint_entity("UPI_ID", upi, feed["source"], feed["scam_type"])
                    synced_iocs += 1
                for url in indicators.get("urls", []):
                    await graph.add_osint_entity("URL", url, feed["source"], feed["scam_type"])
                    synced_iocs += 1
        finally:
            await graph.close()
            
        logger.info(f"OSINT sync complete. Synced {synced_patterns} new patterns and {synced_iocs} IoCs.")
        return {
            "status": "success",
            "synced_patterns": synced_patterns,
            "synced_iocs": synced_iocs
        }
