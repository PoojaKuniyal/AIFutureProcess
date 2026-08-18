import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    import json
    from sqlalchemy.types import UserDefinedType
    
    class Vector(UserDefinedType):
        def __init__(self, dim=384):
            self.dim = dim
            
        def get_col_spec(self, **kw):
            return f"vector({self.dim})"
            
        def bind_processor(self, dialect):
            if dialect.name == "sqlite":
                return lambda value: json.dumps(value) if value is not None else None
            return lambda value: value
            
        def result_processor(self, dialect, coltype):
            if dialect.name == "sqlite":
                return lambda value: json.loads(value) if isinstance(value, str) else value
            return lambda value: value

from app.core.database import Base

class ProcessModel(Base):
    __tablename__ = "processes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False, default="Retail / E-commerce")
    description = Column(Text, nullable=False)
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    current_activities = relationship("CurrentActivityModel", back_populates="process", cascade="all, delete-orphan")
    research_evidence = relationship("ResearchEvidenceModel", back_populates="process", cascade="all, delete-orphan")
    future_processes = relationship("FutureProcessModel", back_populates="process", cascade="all, delete-orphan")

class CurrentActivityModel(Base):
    __tablename__ = "current_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    process_id = Column(String(36), ForeignKey("processes.id", ondelete="CASCADE"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String(100), nullable=False)
    system = Column(String(100), nullable=False)
    operational_problem = Column(Text, nullable=True)

    process = relationship("ProcessModel", back_populates="current_activities")
    evidence_items = relationship("ResearchEvidenceModel", back_populates="activity")

class ResearchEvidenceModel(Base):
    __tablename__ = "research_evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    process_id = Column(String(36), ForeignKey("processes.id", ondelete="CASCADE"), nullable=False)
    transformation_run_id = Column(String(36), ForeignKey("future_processes.id", ondelete="CASCADE"), nullable=True)
    activity_id = Column(String(36), ForeignKey("current_activities.id", ondelete="SET NULL"), nullable=True)
    search_query = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    snippet = Column(Text, nullable=False)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(Vector(384), nullable=True)

    process = relationship("ProcessModel", back_populates="research_evidence")
    activity = relationship("CurrentActivityModel", back_populates="evidence_items")
    future_process = relationship("FutureProcessModel", back_populates="research_evidence")

class FutureProcessModel(Base):
    __tablename__ = "future_processes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())) # transformation_run_id
    process_id = Column(String(36), ForeignKey("processes.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow)

    process = relationship("ProcessModel", back_populates="future_processes")
    future_activities = relationship("FutureActivityModel", back_populates="future_process", cascade="all, delete-orphan")
    research_evidence = relationship("ResearchEvidenceModel", back_populates="future_process", cascade="all, delete-orphan")
    impact_assessment = relationship("ImpactAssessmentModel", back_populates="future_process", uselist=False, cascade="all, delete-orphan")

class FutureActivityModel(Base):
    __tablename__ = "future_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    future_process_id = Column(String(36), ForeignKey("future_processes.id", ondelete="CASCADE"), nullable=False)
    target_activity_id = Column(String(36), ForeignKey("current_activities.id", ondelete="SET NULL"), nullable=True) # Reference to baseline activity
    sequence_order = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    execution_type = Column(String(50), nullable=False) # 'human', 'AI-assisted', 'automated', 'human-in-the-loop'
    rationale = Column(Text, nullable=False)
    primary_system = Column(String(100), nullable=False)
    human_involvement_role = Column(String(100), nullable=True)
    provenance_status = Column(String(50), nullable=False, default="ANALYTIC_RECOMMENDATION")
    linked_evidence_id = Column(String(36), ForeignKey("research_evidence.id", ondelete="SET NULL"), nullable=True)

    future_process = relationship("FutureProcessModel", back_populates="future_activities")
    target_activity = relationship("CurrentActivityModel")
    linked_evidence = relationship("ResearchEvidenceModel", foreign_keys=[linked_evidence_id])

class ImpactAssessmentModel(Base):
    __tablename__ = "impact_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    future_process_id = Column(String(36), ForeignKey("future_processes.id", ondelete="CASCADE"), nullable=False)
    impact_level = Column(String(20), nullable=False) # 'High', 'Medium', 'Low'
    implementation_complexity = Column(String(20), nullable=False) # 'High', 'Medium', 'Low'
    confidence_level = Column(String(20), nullable=False) # 'High', 'Medium', 'Low'
    explicit_assumptions = Column(JSON, nullable=False)
    qualitative_benefits = Column(JSON, nullable=False)
    operational_risks = Column(JSON, nullable=False)
    calculated_roi_notes = Column(Text, nullable=True)

    future_process = relationship("FutureProcessModel", back_populates="impact_assessment")
