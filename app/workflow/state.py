from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict

class ActivityDict(TypedDict):
    activity_id: str
    sequence_order: int
    name: str
    description: str
    role: str
    system: str
    operational_problem: Optional[str]

class EvidenceProvenanceDict(TypedDict):
    evidence_id: str
    target_activity_id: Optional[str]
    search_query: str
    source_url: str
    title: str
    snippet: str
    retrieved_at: str
    relevance_score: float

class AIOpportunityDict(TypedDict):
    opportunity_id: str
    target_activity_id: str
    ai_technology_category: str
    proposed_solution: str
    provenance_type: str  # 'EVIDENCE_BACKED' or 'ANALYTIC_RECOMMENDATION'
    linked_evidence_id: Optional[str]
    rationale: str

class FutureActivityDict(TypedDict):
    activity_id: str
    target_activity_id: Optional[str] # Reference link to baseline activity
    sequence_order: int
    name: str
    execution_type: str  # 'human', 'AI-assisted', 'automated', 'human-in-the-loop'
    rationale: str
    primary_system: str
    human_involvement_role: Optional[str]
    linked_opportunity_id: Optional[str]
    linked_evidence_id: Optional[str]
    provenance_status: str  # 'EVIDENCE_BACKED' or 'ANALYTIC_RECOMMENDATION'

class QualitativeImpactAssessmentDict(TypedDict):
    impact_level: str               # 'High', 'Medium', 'Low'
    implementation_complexity: str  # 'High', 'Medium', 'Low'
    confidence_level: str            # 'High', 'Medium', 'Low'
    explicit_assumptions: List[str]
    qualitative_benefits: List[str]
    operational_risks: List[Dict[str, str]]
    calculated_roi_notes: Optional[str]

class ProcessState(TypedDict):
    transformation_run_id: str
    process_id: str
    process_name: str
    industry: str
    description: str
    is_custom: bool
    current_activities: List[ActivityDict]
    research_queries: List[str]
    research_evidence: List[EvidenceProvenanceDict]
    ai_opportunities: List[AIOpportunityDict]
    future_activities: List[FutureActivityDict]
    impact_assessment: Optional[QualitativeImpactAssessmentDict]
    status: str
    error_message: Optional[str]
