from sqlalchemy import Column, String, Integer, Text, select
from pgvector.sqlalchemy import Vector
import logging
from infrastructure.db.session import Base
logger = logging.getLogger(__name__)

class RegulatoryGuideline(Base):
    __tablename__ = "regulatory_guidelines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    # Using all-MiniLM-L6-v2 which provides 384-dim embeddings
    embedding = Column(Vector(384))

class MistakeCorrection(Base):
    """
    Continuous Learning (RLHF) memory. Stores past cases that human investigators explicitly corrected.
    """
    __tablename__ = "mistake_corrections"
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_scam_text = Column(Text, nullable=False)
    ai_original_decision = Column(Text, nullable=False)
    human_correction = Column(Text, nullable=False)
    embedding = Column(Vector(384))

class FraudPattern(Base):
    """
    Public API OSINT Fraud Data (e.g. from PhishTank, CERT-In, I4C).
    Stores known templates and scripts used by scammers.
    """
    __tablename__ = "fraud_patterns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    embedding = Column(Vector(384))

import asyncio
from sentence_transformers import SentenceTransformer

class KnowledgeBase:
    def __init__(self):
        # We load a small, fast local embedding model (runs purely on CPU)
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
    async def get_embedding(self, text: str) -> list[float]:
        try:
            # We run the embedding synchronously but wrap it in an async-friendly way if needed
            # For this prototype, we'll just run it directly as it's very fast
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate SentenceTransformer embedding: {e}")
            return []

    async def search_relevant_laws(self, db_session, text: str, top_k: int = 2):
        vector = await self.get_embedding(text)
        if not vector:
            return []
            
        try:
            # Cosine distance: RegulatoryGuideline.embedding.cosine_distance(vector)
            stmt = select(RegulatoryGuideline).order_by(
                RegulatoryGuideline.embedding.cosine_distance(vector)
            ).limit(top_k)
            
            result = await db_session.execute(stmt)
            laws = result.scalars().all()
            return [{"title": law.title, "content": law.content, "source": law.source} for law in laws]
        except Exception as e:
            logger.error(f"Failed to search knowledge base (is pgvector extension created?): {e}")
            return []
            
    async def search_past_mistakes(self, db_session, text: str, top_k: int = 1):
        """
        RLHF: Find similar cases where the AI previously made a mistake and was corrected by a human.
        """
        vector = await self.get_embedding(text)
        if not vector:
            return []
            
        try:
            stmt = select(MistakeCorrection).order_by(
                MistakeCorrection.embedding.cosine_distance(vector)
            ).limit(top_k)
            
            result = await db_session.execute(stmt)
            mistakes = result.scalars().all()
            return [{"original_scam": m.original_scam_text, "ai_got_wrong": m.ai_original_decision, "human_correction": m.human_correction} for m in mistakes]
        except Exception as e:
            logger.error(f"Failed to search mistake corrections: {e}")
            return []

    async def search_fraud_patterns(self, db_session, text: str, top_k: int = 1):
        """
        Match incoming text against known public API fraud templates.
        """
        vector = await self.get_embedding(text)
        if not vector:
            return []
            
        try:
            stmt = select(FraudPattern).order_by(
                FraudPattern.embedding.cosine_distance(vector)
            ).limit(top_k)
            
            result = await db_session.execute(stmt)
            patterns = result.scalars().all()
            return [{"pattern": p.pattern_name, "description": p.description} for p in patterns]
        except Exception as e:
            logger.error(f"Failed to search fraud patterns: {e}")
            return []

    async def seed_knowledge_base(self, db_session):
        """
        Seeds the DB with mock RBI and IT Act laws if it's empty.
        """
        try:
            result = await db_session.execute(select(RegulatoryGuideline).limit(1))
            if result.scalar_one_or_none() is not None:
                return # Already seeded
                
            logger.info("Seeding pgvector Knowledge Base with RBI laws...")
            
            mock_laws = [
                {
                    "title": "RBI Guidelines on Digital Arrests",
                    "source": "RBI",
                    "content": "The Reserve Bank of India strictly advises that law enforcement agencies (CBI, Police, Customs) NEVER demand money transfers via RTGS/NEFT to 'safe accounts' over Skype or WhatsApp video calls. Any such demand is definitively a scam."
                },
                {
                    "title": "Section 66D IT Act",
                    "source": "IT Act 2000",
                    "content": "Cheating by personation by using computer resource. Any communication claiming to be a bank official requiring OTP for KYC update is fraudulent."
                }
            ]
            
            for law in mock_laws:
                embedding = await self.get_embedding(law["content"])
                if embedding:
                    db_session.add(RegulatoryGuideline(
                        title=law["title"],
                        source=law["source"],
                        content=law["content"],
                        embedding=embedding
                    ))
                    
            logger.info("Seeding pgvector Knowledge Base with Public Fraud Patterns...")
            mock_patterns = [
                {
                    "name": "CBI Digital Arrest Extortion",
                    "desc": "Scammer calls claiming a parcel in your name was intercepted by Customs containing MDMA drugs. They demand you join a Skype video call for a 'Digital Arrest' statement, then demand a refundable security deposit."
                },
                {
                    "name": "TRAI Mobile Disconnection",
                    "desc": "Automated IVR call claiming your mobile number will be blocked in 2 hours by TRAI due to illegal activities. Press 9 for customer care. Scammer then asks for Aadhaar and OTP."
                }
            ]
            for pattern in mock_patterns:
                embedding = await self.get_embedding(pattern["desc"])
                if embedding:
                    db_session.add(FraudPattern(
                        pattern_name=pattern["name"],
                        description=pattern["desc"],
                        embedding=embedding
                    ))

            await db_session.commit()
            logger.info("Knowledge Base Seeded successfully with Laws and Patterns.")
        except Exception as e:
            logger.error(f"Failed to seed knowledge base. Ensure 'CREATE EXTENSION IF NOT EXISTS vector;' was run: {e}")
