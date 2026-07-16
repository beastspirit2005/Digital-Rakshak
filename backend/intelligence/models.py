from sqlalchemy import Column, String, Float, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.infrastructure.db.session import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class DBInvestigation(Base):
    __tablename__ = "investigations"

    case_id = Column(String, primary_key=True, default=generate_uuid)
    status = Column(String, default="OPEN")
    confidence_score = Column(Float, default=0.0)
    tags = Column(JSON, default=list)

    execution_id = Column(String, ForeignKey("executions.correlation_id"))
    execution = relationship("DBExecution", back_populates="investigation", uselist=False)
    
    evidence = relationship("DBEvidence", back_populates="investigation")

class DBExecution(Base):
    __tablename__ = "executions"

    correlation_id = Column(String, primary_key=True, default=generate_uuid)
    actor_id = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    
    investigation = relationship("DBInvestigation", back_populates="execution")

class DBEvidence(Base):
    __tablename__ = "evidence"

    evidence_id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("investigations.case_id"))
    content_type = Column(String, nullable=False)
    raw_data = Column(String, nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    investigation = relationship("DBInvestigation", back_populates="evidence")
