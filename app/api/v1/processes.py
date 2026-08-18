from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.repositories import ProcessRepository
from app.db.models import ResearchEvidenceModel

router = APIRouter(prefix="/processes", tags=["processes"])

class CurrentActivityCreateSchema(BaseModel):
    name: str = Field(..., example="Demand Forecasting")
    description: Optional[str] = Field(None, example="Manual spreadsheet calculation of store inventory.")
    role: str = Field(..., example="Inventory Planner")
    system: str = Field(..., example="Excel & Legacy ERP")
    operational_problem: Optional[str] = Field(None, example="Long lead time and frequent out-of-stock events.")

class ProcessCreateRequestSchema(BaseModel):
    name: str = Field(..., example="Dynamic Markdown Pricing")
    industry: str = Field(default="Retail / E-commerce")
    description: str = Field(..., example="Process for setting seasonal discounts across online catalog.")
    current_process_text: Optional[str] = Field(None, example="1. Weekly stock audit. 2. Manual price tag updates.")
    problems_text: Optional[str] = Field(None, example="Slow manual updates and pricing errors.")
    activities: Optional[List[CurrentActivityCreateSchema]] = Field(default_factory=list)

@router.get("", response_model=List[Dict[str, Any]])
def list_processes(db: Session = Depends(get_db)):
    processes = ProcessRepository.list_processes(db)
    result = []
    for p in processes:
        result.append({
            "id": p.id,
            "name": p.name,
            "industry": p.industry,
            "description": p.description,
            "is_custom": p.is_custom,
            "activity_count": len(p.current_activities)
        })
    return result

@router.post("", status_code=status.HTTP_201_CREATED)
def create_custom_process(payload: ProcessCreateRequestSchema, db: Session = Depends(get_db)):
    if payload.activities and len(payload.activities) > 0:
        activities_data = [act.dict() for act in payload.activities]
    else:
        from app.services.llm_adapter import LLMAdapter
        activities_data = LLMAdapter.parse_unstructured_process_to_activities(
            process_name=payload.name,
            description=payload.description,
            current_process_text=payload.current_process_text or "",
            problems_text=payload.problems_text or ""
        )

    process = ProcessRepository.create_process(
        db=db,
        name=payload.name,
        industry=payload.industry,
        description=payload.description,
        activities=activities_data,
        is_custom=True
    )
    return {
        "message": "Custom process created successfully.",
        "process_id": process.id,
        "name": process.name,
        "activity_count": len(activities_data)
    }

@router.get("/{process_id}")
def get_process_details(process_id: str, db: Session = Depends(get_db)):
    process = ProcessRepository.get_process_by_id(db, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found.")

    current_activities = [
        {
            "id": act.id,
            "sequence_order": act.sequence_order,
            "name": act.name,
            "description": act.description,
            "role": act.role,
            "system": act.system,
            "operational_problem": act.operational_problem
        }
        for act in sorted(process.current_activities, key=lambda x: x.sequence_order)
    ]

    latest_future = ProcessRepository.get_latest_future_process(db, process_id)
    future_data = None

    if latest_future:
        future_activities = []
        for fact in sorted(latest_future.future_activities, key=lambda x: x.sequence_order):
            linked_ev = None
            if fact.linked_evidence_id:
                ev_obj = db.query(ResearchEvidenceModel).filter(ResearchEvidenceModel.id == fact.linked_evidence_id).first()
                if ev_obj:
                    linked_ev = {
                        "id": ev_obj.id,
                        "title": ev_obj.title,
                        "source_url": ev_obj.source_url,
                        "snippet": ev_obj.snippet,
                        "retrieved_at": ev_obj.retrieved_at.isoformat() if ev_obj.retrieved_at else None
                    }
            
            future_activities.append({
                "id": fact.id,
                "target_activity_id": fact.target_activity_id,
                "sequence_order": fact.sequence_order,
                "name": fact.name,
                "execution_type": fact.execution_type,
                "rationale": fact.rationale,
                "primary_system": fact.primary_system,
                "human_involvement_role": fact.human_involvement_role,
                "provenance_status": fact.provenance_status,
                "linked_evidence_id": fact.linked_evidence_id,
                "linked_evidence": linked_ev
            })

        impact = latest_future.impact_assessment
        impact_data = {
            "impact_level": impact.impact_level,
            "implementation_complexity": impact.implementation_complexity,
            "confidence_level": impact.confidence_level,
            "explicit_assumptions": impact.explicit_assumptions,
            "qualitative_benefits": impact.qualitative_benefits,
            "operational_risks": impact.operational_risks,
            "calculated_roi_notes": impact.calculated_roi_notes
        } if impact else None

        future_data = {
            "id": latest_future.id,
            "transformation_run_id": latest_future.id,
            "status": latest_future.status,
            "created_at": latest_future.created_at.isoformat() if latest_future.created_at else None,
            "future_activities": future_activities,
            "impact_assessment": impact_data
        }

    evidence = ProcessRepository.get_evidence_by_process(db, process_id)
    evidence_data = [
        {
            "id": ev.id,
            "transformation_run_id": ev.transformation_run_id,
            "activity_id": ev.activity_id,
            "search_query": ev.search_query,
            "source_url": ev.source_url,
            "title": ev.title,
            "snippet": ev.snippet,
            "retrieved_at": ev.retrieved_at.isoformat() if ev.retrieved_at else None
        }
        for ev in evidence
    ]

    return {
        "id": process.id,
        "name": process.name,
        "industry": process.industry,
        "description": process.description,
        "is_custom": process.is_custom,
        "current_activities": current_activities,
        "future_process": future_data,
        "evidence_items": evidence_data
    }

@router.delete("/{process_id}")
def delete_process(process_id: str, db: Session = Depends(get_db)):
    success = ProcessRepository.delete_process(db, process_id)
    if not success:
        raise HTTPException(status_code=404, detail="Process not found.")
    return {"message": "Process deleted successfully.", "process_id": process_id}
