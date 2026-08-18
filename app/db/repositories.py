import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import (
    ProcessModel, CurrentActivityModel, ResearchEvidenceModel,
    FutureProcessModel, FutureActivityModel, ImpactAssessmentModel
)

logger = logging.getLogger(__name__)

class ProcessRepository:
    @staticmethod
    def list_processes(db: Session) -> List[ProcessModel]:
        return db.query(ProcessModel).order_by(ProcessModel.created_at.asc()).all()

    @staticmethod
    def get_process_by_id(db: Session, process_id: str) -> Optional[ProcessModel]:
        return db.query(ProcessModel).filter(ProcessModel.id == process_id).first()

    @staticmethod
    def delete_process(db: Session, process_id: str) -> bool:
        process = db.query(ProcessModel).filter(ProcessModel.id == process_id).first()
        if process:
            db.delete(process)
            db.commit()
            return True
        return False

    @staticmethod
    def create_process(
        db: Session,
        name: str,
        industry: str,
        description: str,
        activities: List[Dict[str, Any]],
        is_custom: bool = True
    ) -> ProcessModel:
        process_id = str(uuid.uuid4())
        process = ProcessModel(
            id=process_id,
            name=name,
            industry=industry,
            description=description,
            is_custom=is_custom
        )
        db.add(process)
        db.flush()

        for idx, act in enumerate(activities, 1):
            activity = CurrentActivityModel(
                id=str(uuid.uuid4()),
                process_id=process.id,
                sequence_order=act.get("sequence_order", idx),
                name=act["name"],
                description=act.get("description", ""),
                role=act.get("role", "Operational Staff"),
                system=act.get("system", "Manual / General System"),
                operational_problem=act.get("operational_problem")
            )
            db.add(activity)

        db.commit()
        db.refresh(process)
        return process

    @staticmethod
    def create_future_process_run(db: Session, process_id: str, transformation_run_id: str) -> FutureProcessModel:
        """Initializes the FutureProcessModel record at the start of a transformation run with status=IN_PROGRESS."""
        # Delete old completed/failed future process runs for this process to ensure clean single-active-run state
        old_futures = db.query(FutureProcessModel).filter(FutureProcessModel.process_id == process_id).all()
        for old_f in old_futures:
            db.delete(old_f)
        db.commit()

        future_proc = FutureProcessModel(
            id=transformation_run_id,
            process_id=process_id,
            status="IN_PROGRESS"
        )
        db.add(future_proc)
        db.commit()
        db.refresh(future_proc)
        return future_proc

    @staticmethod
    def clear_research_evidence_for_process(db: Session, process_id: str):
        db.query(ResearchEvidenceModel).filter(ResearchEvidenceModel.process_id == process_id).delete()
        db.commit()

    @staticmethod
    def save_research_evidence(
        db: Session,
        process_id: str,
        activity_id: Optional[str],
        search_query: str,
        source_url: str,
        title: str,
        snippet: str,
        embedding: Optional[List[float]] = None,
        evidence_id: Optional[str] = None,
        transformation_run_id: Optional[str] = None
    ) -> ResearchEvidenceModel:
        ev_id = evidence_id or str(uuid.uuid4())
        evidence = ResearchEvidenceModel(
            id=ev_id,
            process_id=process_id,
            transformation_run_id=transformation_run_id,
            activity_id=activity_id,
            search_query=search_query,
            source_url=source_url,
            title=title,
            snippet=snippet,
            embedding=embedding
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        return evidence

    @staticmethod
    def get_evidence_by_process(db: Session, process_id: str, transformation_run_id: Optional[str] = None) -> List[ResearchEvidenceModel]:
        query = db.query(ResearchEvidenceModel).filter(ResearchEvidenceModel.process_id == process_id)
        if transformation_run_id:
            query = query.filter(ResearchEvidenceModel.transformation_run_id == transformation_run_id)
        return query.order_by(ResearchEvidenceModel.retrieved_at.asc()).all()

    @staticmethod
    def find_similar_evidence(db: Session, process_id: str, query_embedding: List[float], limit: int = 3) -> List[ResearchEvidenceModel]:
        try:
            results = db.query(ResearchEvidenceModel).filter(
                ResearchEvidenceModel.process_id == process_id,
                ResearchEvidenceModel.embedding.isnot(None)
            ).order_by(
                ResearchEvidenceModel.embedding.cosine_distance(query_embedding)
            ).limit(limit).all()
            return results
        except Exception:
            return db.query(ResearchEvidenceModel).filter(ResearchEvidenceModel.process_id == process_id).limit(limit).all()

    @staticmethod
    def save_future_process_results(
        db: Session,
        process_id: str,
        future_activities: List[Dict[str, Any]],
        impact_assessment: Dict[str, Any],
        transformation_run_id: str
    ) -> FutureProcessModel:
        # Fetch existing IN_PROGRESS record created at start of run
        future_proc = db.query(FutureProcessModel).filter(FutureProcessModel.id == transformation_run_id).first()
        if not future_proc:
            future_proc = FutureProcessModel(
                id=transformation_run_id,
                process_id=process_id,
                status="IN_PROGRESS"
            )
            db.add(future_proc)
            db.flush()

        future_proc.status = "COMPLETED"

        for idx, act in enumerate(future_activities, 1):
            future_act = FutureActivityModel(
                id=str(uuid.uuid4()),
                future_process_id=future_proc.id,
                target_activity_id=act.get("target_activity_id"),
                sequence_order=act.get("sequence_order", idx),
                name=act["name"],
                execution_type=act.get("execution_type", "AI-assisted"),
                rationale=act.get("rationale", ""),
                primary_system=act.get("primary_system", "AI-Enhanced System"),
                human_involvement_role=act.get("human_involvement_role"),
                provenance_status=act.get("provenance_status", "ANALYTIC_RECOMMENDATION"),
                linked_evidence_id=act.get("linked_evidence_id")
            )
            db.add(future_act)

        impact = ImpactAssessmentModel(
            id=str(uuid.uuid4()),
            future_process_id=future_proc.id,
            impact_level=impact_assessment.get("impact_level", "Medium"),
            implementation_complexity=impact_assessment.get("implementation_complexity", "Medium"),
            confidence_level=impact_assessment.get("confidence_level", "Medium"),
            explicit_assumptions=impact_assessment.get("explicit_assumptions", []),
            qualitative_benefits=impact_assessment.get("qualitative_benefits", []),
            operational_risks=impact_assessment.get("operational_risks", []),
            calculated_roi_notes=impact_assessment.get("calculated_roi_notes")
        )
        db.add(impact)

        db.commit()
        db.refresh(future_proc)
        return future_proc

    @staticmethod
    def get_latest_future_process(db: Session, process_id: str) -> Optional[FutureProcessModel]:
        return db.query(FutureProcessModel).filter(
            FutureProcessModel.process_id == process_id,
            FutureProcessModel.status == "COMPLETED"
        ).order_by(FutureProcessModel.created_at.desc()).first()
