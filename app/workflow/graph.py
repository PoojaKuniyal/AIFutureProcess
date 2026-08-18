import os
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    StateGraph, END = None, None

from app.core.config import settings
from app.workflow.state import ProcessState
from app.workflow.nodes import (
    node_stage1_process_analysis,
    node_stage2_research_evidence,
    node_stage3_ai_opportunity,
    node_stage4_future_design,
    node_stage5_validation_persistence
)

logger = logging.getLogger(__name__)

def create_process_designer_graph(db_session: Session = None):
    if not HAS_LANGGRAPH:
        return None

    builder = StateGraph(ProcessState)

    def stage1_wrapper(state: ProcessState):
        return node_stage1_process_analysis(state)

    def stage2_wrapper(state: ProcessState):
        return node_stage2_research_evidence(state, db_session=db_session)

    def stage3_wrapper(state: ProcessState):
        return node_stage3_ai_opportunity(state)

    def stage4_wrapper(state: ProcessState):
        return node_stage4_future_design(state)

    def stage5_wrapper(state: ProcessState):
        return node_stage5_validation_persistence(state, db_session=db_session)

    builder.add_node("stage1_process_analysis", stage1_wrapper)
    builder.add_node("stage2_research_evidence", stage2_wrapper)
    builder.add_node("stage3_ai_opportunity", stage3_wrapper)
    builder.add_node("stage4_future_design", stage4_wrapper)
    builder.add_node("stage5_validation_persistence", stage5_wrapper)

    builder.set_entry_point("stage1_process_analysis")
    builder.add_edge("stage1_process_analysis", "stage2_research_evidence")
    builder.add_edge("stage2_research_evidence", "stage3_ai_opportunity")
    builder.add_edge("stage3_ai_opportunity", "stage4_future_design")
    builder.add_edge("stage4_future_design", "stage5_validation_persistence")
    builder.add_edge("stage5_validation_persistence", END)

    return builder.compile()

def run_process_transformation(initial_state: ProcessState, db_session: Session = None) -> ProcessState:
    # Optional LangSmith Tracing Setup
    run_config = None
    if settings.LANGCHAIN_TRACING_V2.lower() == "true" and settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
        run_config = {
            "run_name": f"Transform-{initial_state.get('process_name', 'RetailProcess')}",
            "tags": ["retail-process-designer", initial_state.get("industry", "Retail")],
            "metadata": {"process_id": initial_state.get("process_id")}
        }
        logger.info(f"LangSmith Tracing enabled for project '{settings.LANGCHAIN_PROJECT}'.")

    if HAS_LANGGRAPH:
        graph = create_process_designer_graph(db_session=db_session)
        if run_config:
            final_state = graph.invoke(initial_state, config=run_config)
        else:
            final_state = graph.invoke(initial_state)
    else:
        # Fallback sequential 5-stage invocation for host test environments
        s1 = node_stage1_process_analysis(initial_state)
        initial_state.update(s1)
        s2 = node_stage2_research_evidence(initial_state, db_session=db_session)
        initial_state.update(s2)
        s3 = node_stage3_ai_opportunity(initial_state)
        initial_state.update(s3)
        s4 = node_stage4_future_design(initial_state)
        initial_state.update(s4)
        s5 = node_stage5_validation_persistence(initial_state, db_session=db_session)
        initial_state.update(s5)
        final_state = initial_state

    return final_state
