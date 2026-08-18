import unittest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.config import settings
from app.db.repositories import ProcessRepository
from app.workflow.graph import run_process_transformation

class TestPersistenceAndIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_process_isolation_and_distinct_run_ids(self):
        # 1. Create Process A (Inventory Management)
        proc_a = ProcessRepository.create_process(
            db=self.db,
            name="Inventory Replenishment A",
            industry="Retail",
            description="Inventory replenishment process A",
            activities=[
                {
                    "name": "POS Demand Aggregation",
                    "description": "Aggregate POS sales data",
                    "role": "Inventory Analyst",
                    "system": "Legacy POS",
                    "operational_problem": "Lagging sales data causes stockouts."
                }
            ],
            is_custom=True
        )

        # 2. Create Process B (Customer Service)
        proc_b = ProcessRepository.create_process(
            db=self.db,
            name="Customer Support B",
            industry="Retail",
            description="Customer support ticket process B",
            activities=[
                {
                    "name": "Ticket Triage",
                    "description": "Categorize customer tickets",
                    "role": "Support Agent",
                    "system": "Zendesk",
                    "operational_problem": "Misrouted tickets delay initial response."
                }
            ],
            is_custom=True
        )

        # K6: Untransformed process does not display completed state
        latest_a_pre = ProcessRepository.get_latest_future_process(self.db, proc_a.id)
        latest_b_pre = ProcessRepository.get_latest_future_process(self.db, proc_b.id)
        self.assertIsNone(latest_a_pre)
        self.assertIsNone(latest_b_pre)

        # K1 & K7: Execute Transformation for Process A with LangSmith trace metadata enabled
        settings.LANGCHAIN_TRACING_V2 = "true"
        settings.LANGCHAIN_API_KEY = "test_ls_key"

        run_id_a1 = "run-a1-12345"
        state_a1 = {
            "transformation_run_id": run_id_a1,
            "process_id": proc_a.id,
            "process_name": proc_a.name,
            "industry": proc_a.industry,
            "description": proc_a.description,
            "is_custom": proc_a.is_custom,
            "current_activities": [
                {
                    "activity_id": proc_a.current_activities[0].id,
                    "sequence_order": 1,
                    "name": proc_a.current_activities[0].name,
                    "description": proc_a.current_activities[0].description,
                    "role": proc_a.current_activities[0].role,
                    "system": proc_a.current_activities[0].system,
                    "operational_problem": proc_a.current_activities[0].operational_problem
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

        run_process_transformation(state_a1, db_session=self.db)

        # Verify Process A has completed transformation
        latest_a1 = ProcessRepository.get_latest_future_process(self.db, proc_a.id)
        ev_a1 = ProcessRepository.get_evidence_by_process(self.db, proc_a.id)
        self.assertIsNotNone(latest_a1)
        self.assertEqual(latest_a1.id, run_id_a1)
        self.assertGreater(len(ev_a1), 0)

        # K1 & K5: Process B remains strictly untransformed (Process Isolation)
        latest_b_post_a = ProcessRepository.get_latest_future_process(self.db, proc_b.id)
        ev_b_post_a = ProcessRepository.get_evidence_by_process(self.db, proc_b.id)
        self.assertIsNone(latest_b_post_a)
        self.assertEqual(len(ev_b_post_a), 0)

        # K2 & K4: Execute Transformation for Process B and verify distinct run IDs & process-specific impact
        run_id_b1 = "run-b1-67890"
        state_b1 = {
            "transformation_run_id": run_id_b1,
            "process_id": proc_b.id,
            "process_name": proc_b.name,
            "industry": proc_b.industry,
            "description": proc_b.description,
            "is_custom": proc_b.is_custom,
            "current_activities": [
                {
                    "activity_id": proc_b.current_activities[0].id,
                    "sequence_order": 1,
                    "name": proc_b.current_activities[0].name,
                    "description": proc_b.current_activities[0].description,
                    "role": proc_b.current_activities[0].role,
                    "system": proc_b.current_activities[0].system,
                    "operational_problem": proc_b.current_activities[0].operational_problem
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

        run_process_transformation(state_b1, db_session=self.db)

        latest_b1 = ProcessRepository.get_latest_future_process(self.db, proc_b.id)
        self.assertIsNotNone(latest_b1)

        # K2: Assert distinct transformation run IDs
        self.assertNotEqual(latest_a1.id, latest_b1.id)
        self.assertEqual(latest_b1.id, run_id_b1)

        # K4: Assert impact/benefits are process-specific and not identical static text
        impact_a = latest_a1.impact_assessment
        impact_b = latest_b1.impact_assessment

        self.assertIsNotNone(impact_a)
        self.assertIsNotNone(impact_b)
        # Benefits for Process A mention POS/stockouts, while Process B mention tickets/triage
        benefits_a_text = " ".join(impact_a.qualitative_benefits)
        benefits_b_text = " ".join(impact_b.qualitative_benefits)
        
        self.assertIn("POS Demand Aggregation", benefits_a_text)
        self.assertIn("Ticket Triage", benefits_b_text)
        self.assertNotEqual(benefits_a_text, benefits_b_text)

        # K2: Execute second run on Process A and verify new distinct run ID replaces previous
        run_id_a2 = "run-a2-99999"
        state_a2 = dict(state_a1)
        state_a2["transformation_run_id"] = run_id_a2
        run_process_transformation(state_a2, db_session=self.db)

        latest_a2 = ProcessRepository.get_latest_future_process(self.db, proc_a.id)
        self.assertEqual(latest_a2.id, run_id_a2)
        self.assertNotEqual(latest_a2.id, run_id_a1)

    def test_unstructured_custom_process_extraction_and_transformation(self):
        from app.services.llm_adapter import LLMAdapter
        
        proc_text = (
            "Step 1: Customer submits product return request online.\n"
            "Step 2: Warehouse worker inspects returned item manually.\n"
            "Step 3: Refund is issued to customer credit card."
        )
        prob_text = "Manual inspection is slow and error-prone. Refunds take 14 days to process."
        
        extracted = LLMAdapter.parse_unstructured_process_to_activities(
            process_name="E-Commerce Returns",
            description="End-to-end retail returns workflow",
            current_process_text=proc_text,
            problems_text=prob_text
        )
        
        self.assertGreaterEqual(len(extracted), 2)
        for act in extracted:
            self.assertIn("role", act)
            self.assertIn("system", act)
            self.assertIn("operational_problem", act)

        custom_proc = ProcessRepository.create_process(
            db=self.db,
            name="E-Commerce Returns",
            industry="Retail / E-commerce",
            description="End-to-end retail returns workflow",
            activities=extracted,
            is_custom=True
        )
        
        self.assertIsNotNone(custom_proc.id)
        self.assertEqual(len(custom_proc.current_activities), len(extracted))

        run_id = "run-returns-101"
        state = {
            "transformation_run_id": run_id,
            "process_id": custom_proc.id,
            "process_name": custom_proc.name,
            "industry": custom_proc.industry,
            "description": custom_proc.description,
            "is_custom": custom_proc.is_custom,
            "current_activities": [
                {
                    "activity_id": act.id,
                    "sequence_order": act.sequence_order,
                    "name": act.name,
                    "description": act.description,
                    "role": act.role,
                    "system": act.system,
                    "operational_problem": act.operational_problem
                }
                for act in custom_proc.current_activities
            ],
            "research_queries": [],
            "research_evidence": [],
            "ai_opportunities": [],
            "future_activities": [],
            "impact_assessment": None,
            "status": "INITIATED",
            "error_message": None
        }

        final_state = run_process_transformation(state, db_session=self.db)
        self.assertEqual(final_state["status"], "COMPLETED")
        self.assertGreater(len(final_state["future_activities"]), 0)

        # Test process deletion
        deleted = ProcessRepository.delete_process(self.db, custom_proc.id)
        self.assertTrue(deleted)
        self.assertIsNone(ProcessRepository.get_process_by_id(self.db, custom_proc.id))

    def test_customer_returns_and_refund_management_role_extraction_and_mapping(self):
        from app.services.llm_adapter import LLMAdapter
        
        process_name = "Customer Returns & Refund Management"
        description = "Process for receiving, inspecting, and refunding customer merchandise returns."
        proc_text = (
            "1. Support staff receive return requests from customers via Zendesk email ticket.\n"
            "2. Store or warehouse staff inspect returned items and verify product condition.\n"
            "3. Finance team approves and processes refunds to customer payment accounts.\n"
            "4. Inventory staff update warehouse stock counts in the ERP system."
        )
        prob_text = (
            "- Support staff experience high triage delays handling email tickets.\n"
            "- Store or warehouse staff manual inspection causes bottlenecks and item grading errors.\n"
            "- Finance manual refund processing takes 10 to 14 days.\n"
            "- Inventory stock count updates lag behind actual returns causing stock discrepancies."
        )
        
        extracted = LLMAdapter.parse_unstructured_process_to_activities(
            process_name=process_name,
            description=description,
            current_process_text=proc_text,
            problems_text=prob_text
        )
        
        self.assertEqual(len(extracted), 4)
        
        roles = [act["role"] for act in extracted]
        systems = [act["system"] for act in extracted]
        
        self.assertTrue(any("Support" in r or "Staff" in r for r in roles))
        self.assertTrue(any("Warehouse" in r or "Store" in r for r in roles))
        self.assertTrue(any("Finance" in r for r in roles))
        self.assertTrue(any("Inventory" in r for r in roles))
        
        self.assertTrue(any("Zendesk" in s for s in systems))
        self.assertTrue(any("Erp" in s or "ERP" in s for s in systems))
        
        custom_proc = ProcessRepository.create_process(
            db=self.db,
            name=process_name,
            industry="Retail / E-commerce",
            description=description,
            activities=extracted,
            is_custom=True
        )
        
        self.assertIsNotNone(custom_proc.id)
        self.assertEqual(len(custom_proc.current_activities), 4)
        
        act1 = custom_proc.current_activities[0]
        act3 = custom_proc.current_activities[2]
        
        self.assertIn("triage", act1.operational_problem.lower())
        self.assertIn("refund", act3.operational_problem.lower())
        
        run_id = "run-returns-demo-202"
        state = {
            "transformation_run_id": run_id,
            "process_id": custom_proc.id,
            "process_name": custom_proc.name,
            "industry": custom_proc.industry,
            "description": custom_proc.description,
            "is_custom": custom_proc.is_custom,
            "current_activities": [
                {
                    "activity_id": act.id,
                    "sequence_order": act.sequence_order,
                    "name": act.name,
                    "description": act.description,
                    "role": act.role,
                    "system": act.system,
                    "operational_problem": act.operational_problem
                }
                for act in custom_proc.current_activities
            ],
            "research_queries": [],
            "research_evidence": [],
            "ai_opportunities": [],
            "future_activities": [],
            "impact_assessment": None,
            "status": "INITIATED",
            "error_message": None
        }

        final_state = run_process_transformation(state, db_session=self.db)
        self.assertEqual(final_state["status"], "COMPLETED")
        self.assertGreater(len(final_state["future_activities"]), 0)

if __name__ == "__main__":
    unittest.main()
