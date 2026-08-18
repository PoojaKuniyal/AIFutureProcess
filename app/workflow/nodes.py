import uuid
import datetime
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.workflow.state import (
    ProcessState, EvidenceProvenanceDict, AIOpportunityDict,
    FutureActivityDict, QualitativeImpactAssessmentDict
)
from app.services.research_service import ResearchService
from app.services.embedding_service import EmbeddingService
from app.services.llm_adapter import LLMAdapter
from app.db.repositories import ProcessRepository

logger = logging.getLogger(__name__)

def node_stage1_process_analysis(state: ProcessState) -> Dict[str, Any]:
    """Stage 1: Process Analysis & Query Formulation."""
    activities = state.get("current_activities", [])
    process_name = state.get("process_name", "Business Process")
    industry = state.get("industry", "").strip()

    if industry and industry.lower() not in process_name.lower():
        context_prefix = f"{industry} {process_name}"
    else:
        context_prefix = process_name
    
    queries = []
    for act in activities:
        prob = act.get("operational_problem") or act.get("description") or act.get("name")
        prob_str = prob[:80] if prob and prob != "Not specified" else ""
        query = f"{context_prefix} AI automation solution for {act['name']} {prob_str}".strip()
        queries.append(query)
        
    return {
        "research_queries": queries,
        "status": "STAGE1_COMPLETED"
    }

def node_stage2_research_evidence(state: ProcessState, db_session: Session = None) -> Dict[str, Any]:
    """Stage 2: Live External Research & Vector Indexing."""
    queries = state.get("research_queries", [])
    process_id = state.get("process_id")
    process_name = state.get("process_name", "Business Process")
    run_id = state.get("transformation_run_id")
    activities = state.get("current_activities", [])
    
    discovered_evidence: List[EvidenceProvenanceDict] = []
    
    if db_session and process_id:
        try:
            ProcessRepository.clear_research_evidence_for_process(db_session, process_id)
        except Exception as e:
            logger.error(f"Error clearing previous research evidence for process {process_id}: {e}", exc_info=True)
    
    for idx, query in enumerate(queries):
        activity_id = activities[idx]["activity_id"] if idx < len(activities) else None
        search_results = ResearchService.search(query, max_results=2)
        
        for item in search_results:
            ev_id = f"ev-{uuid.uuid4().hex[:8]}"
            snippet = item.get("snippet", "")
            title = item.get("title", f"{process_name} AI Research")
            url = item.get("source_url", "https://duckduckgo.com")
            
            embedding = EmbeddingService.embed_text(f"{title} {snippet}")
            
            if db_session and process_id:
                try:
                    saved_ev = ProcessRepository.save_research_evidence(
                        db=db_session,
                        process_id=process_id,
                        activity_id=activity_id,
                        search_query=query,
                        source_url=url,
                        title=title,
                        snippet=snippet,
                        embedding=embedding,
                        evidence_id=ev_id,
                        transformation_run_id=run_id
                    )
                    ev_id = saved_ev.id
                except Exception as e:
                    # Constraint 2: Do NOT silently swallow persistence errors
                    logger.error(
                        f"CRITICAL: Failed to persist research evidence for process_id='{process_id}', "
                        f"transformation_run_id='{run_id}', activity_id='{activity_id}': {e}",
                        exc_info=True
                    )
                    return {
                        "error_message": f"Failed to persist research evidence: {e}",
                        "status": "STAGE2_FAILED"
                    }
            
            discovered_evidence.append({
                "evidence_id": ev_id,
                "target_activity_id": activity_id,
                "search_query": query,
                "source_url": url,
                "title": title,
                "snippet": snippet,
                "retrieved_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                "relevance_score": 0.85
            })

    return {
        "research_evidence": discovered_evidence,
        "status": "STAGE2_COMPLETED"
    }

def node_stage3_ai_opportunity(state: ProcessState) -> Dict[str, Any]:
    """Stage 3: AI Opportunity Analysis & Mandatory Evidence Provenance Linkage."""
    activities = state.get("current_activities", [])
    evidence_items = state.get("research_evidence", [])
    process_name = state.get("process_name", "Business Process")
    industry = state.get("industry", "")
    
    opportunities: List[AIOpportunityDict] = []
    
    for act in activities:
        act_id = act.get("activity_id")
        act_name = act.get("name", "")
        problem = act.get("operational_problem") or "Manual processing bottleneck."
        
        matching_evidence = [e for e in evidence_items if e.get("target_activity_id") == act_id]
        
        if matching_evidence:
            ev = matching_evidence[0]
            prov_type = "EVIDENCE_BACKED"
            ev_id = ev["evidence_id"]
            rationale = f"Supported by research '{ev['title']}': {ev['snippet'][:120]}..."
        else:
            prov_type = "ANALYTIC_RECOMMENDATION"
            ev_id = None
            rationale = f"AI analytical suggestion based on {process_name} optimization heuristics (Not backed by live external evidence)."
            
        opp_id = f"opp-{uuid.uuid4().hex[:8]}"
        
        tech_cat = _derive_tech_category(act_name, problem, industry=industry, process_name=process_name)
        solution = _derive_solution(act_name, problem, tech_cat, process_name=process_name)
        
        opportunities.append({
            "opportunity_id": opp_id,
            "target_activity_id": act_id,
            "ai_technology_category": tech_cat,
            "proposed_solution": solution,
            "provenance_type": prov_type,
            "linked_evidence_id": ev_id,
            "rationale": rationale
        })

    return {
        "ai_opportunities": opportunities,
        "status": "STAGE3_COMPLETED"
    }

def node_stage4_future_design(state: ProcessState) -> Dict[str, Any]:
    """Stage 4: Future Process Design & Responsibility Assignment."""
    activities = state.get("current_activities", [])
    opportunities = state.get("ai_opportunities", [])
    process_name = state.get("process_name", "Business Process")
    
    opp_map = {o["target_activity_id"]: o for o in opportunities}
    future_activities: List[FutureActivityDict] = []
    
    for idx, act in enumerate(activities, 1):
        act_id = act.get("activity_id")
        opp = opp_map.get(act_id)
        
        exec_type, sys_name, role_name = _classify_responsibility(act, opp, process_name)
        
        prov_status = opp.get("provenance_type", "ANALYTIC_RECOMMENDATION") if opp else "ANALYTIC_RECOMMENDATION"
        linked_ev_id = opp.get("linked_evidence_id") if opp else None
        
        rationale_text = (
            f"Re-architected via {opp['proposed_solution']}. {opp['rationale']}"
            if opp else "Standard human workflow maintained for manual governance."
        )
        
        gen_fact_id = f"fact-{uuid.uuid4().hex[:8]}"
        future_activities.append({
            "activity_id": gen_fact_id,
            "target_activity_id": act_id, # Source baseline reference activity ID
            "sequence_order": idx,
            "name": f"AI-Enhanced {act['name']}" if exec_type != "human" else act["name"],
            "execution_type": exec_type,
            "rationale": rationale_text,
            "primary_system": sys_name,
            "human_involvement_role": role_name,
            "linked_opportunity_id": opp.get("opportunity_id") if opp else None,
            "linked_evidence_id": linked_ev_id,
            "provenance_status": prov_status
        })

    return {
        "future_activities": future_activities,
        "status": "STAGE4_COMPLETED"
    }

def node_stage5_validation_persistence(state: ProcessState, db_session: Session = None) -> Dict[str, Any]:
    """Stage 5: Dynamic Process-Grounded Validation & Database Persistence."""
    process_id = state.get("process_id", "unknown-proc")
    process_name = state.get("process_name", "Business Process")
    run_id = state.get("transformation_run_id") or f"run-{uuid.uuid4().hex[:8]}"
    current_activities = state.get("current_activities", [])
    future_activities = state.get("future_activities", [])
    research_evidence = state.get("research_evidence", [])
    
    # Constraint 3: Process-Specific Dynamic Impact & Complexity Derivation
    auto_count = sum(1 for a in future_activities if a["execution_type"] in ["automated", "AI-assisted", "human-in-the-loop"])
    total_count = len(future_activities) or 1
    automation_ratio = auto_count / total_count
    
    impact_lvl = "High" if automation_ratio >= 0.5 else "Medium"
    
    unique_systems = len(set(a.get("primary_system", "") for a in future_activities if a.get("primary_system")))
    complexity_lvl = "High" if unique_systems >= 3 else ("Medium" if unique_systems >= 2 else "Low")
    
    evidence_backed_count = sum(1 for a in future_activities if a.get("provenance_status") == "EVIDENCE_BACKED")
    confidence_lvl = "High" if evidence_backed_count > 0 else "Medium"
    
    # Process-Grounded Dynamic Qualitative Benefits
    qual_benefits = []
    for act in current_activities:
        prob = act.get("operational_problem")
        if prob and prob != "Not specified":
            qual_benefits.append(f"Resolves operational bottleneck in '{act['name']}': {prob[:110]}")
        else:
            qual_benefits.append(f"Optimizes throughput and eliminates operational friction in '{act['name']}'.")
            
    if research_evidence:
        top_ev = research_evidence[0]
        qual_benefits.append(f"Backed by empirical industry research ('{top_ev['title']}').")
        
    qual_benefits.append(f"Establishes structured human-in-the-loop governance for AI-assisted activities in {process_name}.")
    
    # Process-Grounded Dynamic Operational Risks & Mitigations
    op_risks = []
    systems_list = list(set([a.get("primary_system", "") for a in future_activities if a.get("primary_system")]))
    systems_str = ", ".join(systems_list) if systems_list else "legacy enterprise platforms"
    
    if any(a["execution_type"] == "automated" for a in future_activities):
        auto_acts = [a['name'] for a in future_activities if a["execution_type"] == "automated"]
        op_risks.append({
            "risk": f"Automated execution failure in '{auto_acts[0]}'",
            "mitigation": f"Deploy automated exception handlers and real-time supervisor alert boundaries."
        })
        
    if any(a["execution_type"] in ["AI-assisted", "human-in-the-loop"] for a in future_activities):
        op_risks.append({
            "risk": f"System integration latency across {systems_str}",
            "mitigation": "Implement asynchronous message queues and local Redis/caching layer for operational state."
        })
        
    op_risks.append({
        "risk": f"Staff change management & role adaptation for {process_name} team",
        "mitigation": "Provide interactive human-in-the-loop UI review screens and role-based training modules."
    })
    
    # Process-Grounded Dynamic Explicit Assumptions
    roles_list = list(set([act.get("role") for act in current_activities if act.get("role") and act.get("role") != "Not specified"]))
    roles_str = ", ".join(roles_list) if roles_list else "Operational personnel"
    
    assumptions = [
        f"Primary enterprise systems ({systems_str}) expose REST API or database connector interfaces.",
        f"Operational personnel in roles ({roles_str}) participate in human-in-the-loop exception reviews.",
        f"Operational activity logs and data streams from {systems_str} are ingested daily into {process_name} AI services."
    ]
    
    impact_assessment: QualitativeImpactAssessmentDict = {
        "impact_level": impact_lvl,
        "implementation_complexity": complexity_lvl,
        "confidence_level": confidence_lvl,
        "explicit_assumptions": assumptions,
        "qualitative_benefits": qual_benefits,
        "operational_risks": op_risks,
        "calculated_roi_notes": None
    }
    
    saved_proc = None
    if db_session and process_id:
        try:
            saved_proc = ProcessRepository.save_future_process_results(
                db=db_session,
                process_id=process_id,
                future_activities=future_activities,
                impact_assessment=impact_assessment,
                transformation_run_id=run_id
            )
        except Exception as e:
            # Constraint 2: Do NOT silently swallow persistence errors
            logger.error(
                f"CRITICAL: Failed to persist future process results for process_id='{process_id}', "
                f"transformation_run_id='{run_id}': {e}",
                exc_info=True
            )
            return {
                "error_message": f"Failed to persist future process results: {e}",
                "status": "STAGE5_FAILED"
            }
            
    # Requirement J: Structured backend logging for transformation debugging
    baseline_target_ids = [a.get("activity_id") for a in current_activities]
    gen_future_ids = [fa.get("activity_id") for fa in future_activities]
    impact_assessment_id = saved_proc.impact_assessment.id if (saved_proc and saved_proc.impact_assessment) else "in-memory"
    
    logger.info(
        f"\n================ TRANSFORMATION RUN DEBUG LOG ================\n"
        f"  process_id:              {process_id}\n"
        f"  transformation_run_id:   {run_id}\n"
        f"  future_process_id:       {saved_proc.id if saved_proc else run_id}\n"
        f"  baseline target_ids:     {baseline_target_ids}\n"
        f"  generated future_ids:    {gen_future_ids}\n"
        f"  evidence_count:          {len(research_evidence)}\n"
        f"  impact_assessment_id:    {impact_assessment_id}\n"
        f"=============================================================="
    )
            
    return {
        "impact_assessment": impact_assessment,
        "status": "COMPLETED"
    }

def _derive_tech_category(act_name: str, problem: str, industry: str = "", process_name: str = "") -> str:
    combined = (act_name + " " + problem + " " + industry + " " + process_name).lower()
    if any(k in combined for k in ["document", "paperwork", "form", "verification", "identity", "compliance", "audit", "contract", "id"]):
        return "Autonomous Document AI & Intelligent Verification"
    elif any(k in combined for k in ["ticket", "inquiry", "support", "chat", "onboarding", "orientation", "portal", "training", "helpdesk", "email"]):
        return "Generative Agent & Conversational Assistant"
    elif any(k in combined for k in ["forecast", "demand", "sales", "reorder", "quantity", "predict", "analytic", "scoring"]):
        return "Predictive Analytics & ML Forecasting"
    elif any(k in combined for k in ["pick", "pack", "inspect", "returned", "warehouse", "vision", "image", "hardware"]):
        return "Computer Vision & Robotics Automation"
    elif any(k in combined for k in ["vendor", "scorecard", "po", "purchase", "provisioning", "account", "setup"]):
        return "Autonomous Document AI & Workflow Robotics"
    return "Intelligent Business Process Automation"

def _derive_solution(act_name: str, problem: str, tech_cat: str, process_name: str = "") -> str:
    prob_desc = f", resolve '{problem[:60]}'" if problem and problem != "Not specified" else ""
    return f"Deploy {tech_cat} engine to streamline '{act_name}'{prob_desc}, and trigger automated workflow actions."

def _classify_responsibility(act: Dict[str, Any], opp: Dict[str, Any], process_name: str = ""):
    cat = opp.get("ai_technology_category", "") if opp else ""
    act_role = act.get("role") if act.get("role") and act.get("role") != "Not specified" else None
    act_sys = act.get("system") if act.get("system") and act.get("system") != "Not specified" else None

    human_role = act_role or "Domain Specialist Reviewer"

    if act_sys:
        primary_sys = f"{act_sys} + AI Agent"
    else:
        primary_sys = f"Enterprise Platform ({process_name})"

    if "Predictive Analytics" in cat or "Conversational Assistant" in cat:
        return "AI-assisted", primary_sys, human_role
    elif "Robotics" in cat or "Document AI" in cat:
        governance_role = f"{act_role} (Exception Oversight)" if act_role else None
        return "automated", primary_sys if act_sys else f"Automated Workflow Engine ({cat})", governance_role
    else:
        return "human-in-the-loop", primary_sys, human_role
