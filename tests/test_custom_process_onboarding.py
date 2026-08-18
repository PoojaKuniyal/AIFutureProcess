import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.db.repositories import ProcessRepository
from app.workflow.graph import run_process_transformation
from app.workflow.nodes import (
    node_stage1_process_analysis,
    node_stage2_research_evidence,
    node_stage3_ai_opportunity,
    node_stage4_future_design,
    node_stage5_validation_persistence
)

class TestCustomProcessEmployeeOnboarding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_employee_onboarding_pipeline_not_retail_specific(self):
        # 1. Create Custom Process: Employee Onboarding in Human Resources
        proc = ProcessRepository.create_process(
            db=self.db,
            name="Employee Onboarding",
            industry="Human Resources",
            description="End-to-end new hire onboarding, document collection, IT account provisioning, and orientation.",
            activities=[
                {
                    "name": "Document Collection & Identity Verification",
                    "description": "Collect I-9 forms, tax documents, and ID verification from new hire",
                    "role": "HR Specialist",
                    "system": "Workday & Email",
                    "operational_problem": "Manual paperwork collection causes 5-day delay in onboarding start date."
                },
                {
                    "name": "IT Provisioning & Account Creation",
                    "description": "Provision SSO accounts, email, and laptop hardware for new hire",
                    "role": "IT Administrator",
                    "system": "Active Directory & Jira",
                    "operational_problem": "Manual account creation requests result in missing access permissions on day one."
                },
                {
                    "name": "Orientation & Policy Training",
                    "description": "Conduct company orientation and assign compliance training modules",
                    "role": "Onboarding Coordinator",
                    "system": "LMS & Zoom",
                    "operational_problem": "Manual training scheduling causes compliance tracking gaps."
                }
            ],
            is_custom=True
        )

        run_id = "run-onboarding-test-001"
        initial_state = {
            "transformation_run_id": run_id,
            "process_id": proc.id,
            "process_name": proc.name,
            "industry": proc.industry,
            "description": proc.description,
            "is_custom": proc.is_custom,
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
                for act in proc.current_activities
            ],
            "research_queries": [],
            "research_evidence": [],
            "ai_opportunities": [],
            "future_activities": [],
            "impact_assessment": None,
            "status": "INITIATED",
            "error_message": None
        }

        # Forbidden retail terms to verify against (word boundaries to prevent false positives like 'expose' matching 'pos')
        forbidden_terms = ["retail", "pos", "inventory", "supply chain"]

        # Helper for word boundary checking
        import re
        def check_no_forbidden(text_to_check: str, context_label: str):
            text_lower = text_to_check.lower()
            for term in forbidden_terms:
                pattern = r'\b' + re.escape(term) + r'\b'
                self.assertIsNone(
                    re.search(pattern, text_lower),
                    f"{context_label} contains forbidden retail term '{term}': {text_to_check}"
                )

        # Stage 1 Execution & Verification
        res1 = node_stage1_process_analysis(initial_state)
        queries = res1["research_queries"]
        self.assertEqual(len(queries), 3)
        for q in queries:
            check_no_forbidden(q, "Stage 1 research query")
            self.assertTrue("human resources" in q.lower() or "employee onboarding" in q.lower(), f"Query missing HR context: {q}")
        
        # Positive HR concept verification for Stage 1
        self.assertTrue(any("document collection" in q.lower() for q in queries))
        self.assertTrue(any("it provisioning" in q.lower() for q in queries))

        initial_state.update(res1)

        # Stage 2 Execution & Verification
        res2 = node_stage2_research_evidence(initial_state, db_session=self.db)
        evidence = res2["research_evidence"]
        self.assertGreaterEqual(len(evidence), 3)
        for ev in evidence:
            ev_text = f"{ev['title']} {ev['snippet']}"
            check_no_forbidden(ev_text, "Stage 2 research evidence")
            
        # Positive HR concept verification for Stage 2
        hr_evidence_keywords = ["onboarding", "document", "provisioning", "training", "hr", "automation", "workflow"]
        self.assertTrue(
            any(any(kw in f"{ev['title']} {ev['snippet']}".lower() for kw in hr_evidence_keywords) for ev in evidence),
            "Research evidence lacks relevant HR/Onboarding concepts."
        )

        initial_state.update(res2)

        # Stage 3 Execution & Verification
        res3 = node_stage3_ai_opportunity(initial_state)
        opps = res3["ai_opportunities"]
        self.assertEqual(len(opps), 3)
        for opp in opps:
            opp_text = f"{opp['ai_technology_category']} {opp['proposed_solution']} {opp['rationale']}"
            check_no_forbidden(opp_text, "Stage 3 AI opportunity")

        # Positive HR concept verification for Stage 3
        tech_cats = [opp["ai_technology_category"] for opp in opps]
        self.assertTrue(any("Document AI" in cat for cat in tech_cats), f"Expected Document AI in tech categories: {tech_cats}")
        self.assertTrue(any("Conversational Assistant" in cat or "Workflow" in cat for cat in tech_cats))

        initial_state.update(res3)

        # Stage 4 Execution & Verification
        res4 = node_stage4_future_design(initial_state)
        future_acts = res4["future_activities"]
        self.assertEqual(len(future_acts), 3)
        for fact in future_acts:
            fact_text = f"{fact['name']} {fact['primary_system']} {fact.get('human_involvement_role') or ''} {fact['rationale']}"
            check_no_forbidden(fact_text, "Stage 4 future activity")

        # Positive HR concept verification for Stage 4 systems and roles
        systems_used = [fa["primary_system"] for fa in future_acts]
        roles_used = [fa["human_involvement_role"] for fa in future_acts if fa.get("human_involvement_role")]
        
        self.assertTrue(any("Workday" in s for s in systems_used), f"Expected Workday in primary systems: {systems_used}")
        self.assertTrue(any("Active Directory" in s or "Jira" in s for s in systems_used), f"Expected IT systems in primary systems: {systems_used}")
        self.assertTrue(any("HR Specialist" in r for r in roles_used), f"Expected HR Specialist in roles: {roles_used}")

        initial_state.update(res4)

        # Stage 5 Execution & Verification
        res5 = node_stage5_validation_persistence(initial_state, db_session=self.db)
        impact = res5["impact_assessment"]
        self.assertIsNotNone(impact)

        assumptions_text = " ".join(impact["explicit_assumptions"])
        benefits_text = " ".join(impact["qualitative_benefits"])
        risks_text = " ".join(r["risk"] + " " + r["mitigation"] for r in impact["operational_risks"])
        all_impact_text = f"{assumptions_text} {benefits_text} {risks_text}"

        check_no_forbidden(all_impact_text, "Stage 5 impact assessment")

        # Positive HR/Onboarding concept verification for Stage 5 Impact & Assumptions
        self.assertIn("workday", assumptions_text.lower())
        self.assertIn("hr specialist", assumptions_text.lower())
        self.assertIn("employee onboarding", benefits_text.lower())
        self.assertIn("document collection & identity verification", benefits_text.lower())
        self.assertIn("employee onboarding team", risks_text.lower())

        # 5-Stage Graph Workflow Full Run Verification
        final_state = run_process_transformation(initial_state, db_session=self.db)
        self.assertEqual(final_state["status"], "COMPLETED")

if __name__ == "__main__":
    unittest.main()
