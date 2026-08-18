import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.db.repositories import ProcessRepository
from app.workflow.graph import run_process_transformation

router = APIRouter(prefix="/processes", tags=["transform"])

@router.post("/{process_id}/transform")
def transform_process(process_id: str, db: Session = Depends(get_db)):
    process = ProcessRepository.get_process_by_id(db, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found.")

    current_acts = [
        {
            "activity_id": act.id,
            "sequence_order": act.sequence_order,
            "name": act.name,
            "description": act.description or "",
            "role": act.role,
            "system": act.system,
            "operational_problem": act.operational_problem
        }
        for act in sorted(process.current_activities, key=lambda x: x.sequence_order)
    ]

    # Generate single unique transformation_run_id for the entire workflow execution
    run_id = f"run-{uuid.uuid4().hex[:12]}"

    # Constraint 1: Create FutureProcessModel record in PostgreSQL BEFORE Stage 2 runs
    ProcessRepository.create_future_process_run(db=db, process_id=process.id, transformation_run_id=run_id)

    initial_state = {
        "transformation_run_id": run_id,
        "process_id": process.id,
        "process_name": process.name,
        "industry": process.industry,
        "description": process.description,
        "is_custom": process.is_custom,
        "current_activities": current_acts,
        "research_queries": [],
        "research_evidence": [],
        "ai_opportunities": [],
        "future_activities": [],
        "impact_assessment": None,
        "status": "INITIATED",
        "error_message": None
    }

    # Execute 5-stage LangGraph workflow
    final_state = run_process_transformation(initial_state, db_session=db)

    if final_state.get("error_message"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transformation failed during persistence: {final_state['error_message']}"
        )

    return {
        "message": "Process transformation completed successfully.",
        "process_id": process.id,
        "transformation_run_id": run_id,
        "status": final_state.get("status"),
        "evidence_count": len(final_state.get("research_evidence", [])),
        "future_activities_count": len(final_state.get("future_activities", [])),
        "impact_assessment": final_state.get("impact_assessment")
    }

@router.get("/{process_id}/evidence")
def get_process_evidence(process_id: str, db: Session = Depends(get_db)):
    process = ProcessRepository.get_process_by_id(db, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found.")

    evidence = ProcessRepository.get_evidence_by_process(db, process_id)
    return [
        {
            "evidence_id": ev.id,
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
