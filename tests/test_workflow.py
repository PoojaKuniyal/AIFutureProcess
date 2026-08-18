import unittest
from app.workflow.state import ProcessState
from app.workflow.nodes import (
    node_stage1_process_analysis,
    node_stage2_research_evidence,
    node_stage3_ai_opportunity,
    node_stage4_future_design,
    node_stage5_validation_persistence
)

class TestWorkflowSlice(unittest.TestCase):
    def test_vertical_slice_workflow_execution(self):
        initial_state: ProcessState = {
            "process_id": "test-inv-001",
            "process_name": "Inventory Management / Replenishment",
            "industry": "Retail / E-commerce",
            "description": "Inventory demand forecasting test process",
            "is_custom": False,
            "current_activities": [
                {
                    "activity_id": "act-1",
                    "sequence_order": 1,
                    "name": "Historical Sales Data Aggregation",
                    "description": "Aggregate POS sales data",
                    "role": "Inventory Analyst",
                    "system": "Excel",
                    "operational_problem": "Manual spreadsheet copy-paste errors and 15 hour weekly lag."
                }
            ],
            "research_queries": [],
            "research_evidence": [],
            "ai_opportunities": [],
            "future_activities": [],
            "impact_assessment": None,
            "status": "INITIATED",
            "error_message": None
        }

        # Stage 1
        res1 = node_stage1_process_analysis(initial_state)
        self.assertEqual(len(res1["research_queries"]), 1)
        initial_state.update(res1)

        # Stage 2
        res2 = node_stage2_research_evidence(initial_state)
        self.assertGreaterEqual(len(res2["research_evidence"]), 1)
        initial_state.update(res2)

        # Stage 3
        res3 = node_stage3_ai_opportunity(initial_state)
        self.assertEqual(len(res3["ai_opportunities"]), 1)
        opp = res3["ai_opportunities"][0]
        self.assertIn(opp["provenance_type"], ["EVIDENCE_BACKED", "ANALYTIC_RECOMMENDATION"])
        initial_state.update(res3)

        # Stage 4
        res4 = node_stage4_future_design(initial_state)
        self.assertEqual(len(res4["future_activities"]), 1)
        fact = res4["future_activities"][0]
        self.assertIn(fact["execution_type"], ["human", "AI-assisted", "automated", "human-in-the-loop"])
        initial_state.update(res4)

        # Stage 5
        res5 = node_stage5_validation_persistence(initial_state)
        impact = res5["impact_assessment"]
        self.assertIn(impact["impact_level"], ["High", "Medium", "Low"])
        self.assertIsNone(impact["calculated_roi_notes"])  # Strict rule: No unsupported numerical ROI percentages

if __name__ == "__main__":
    unittest.main()
