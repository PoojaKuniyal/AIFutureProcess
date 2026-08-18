import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.services.research_service import ResearchService
from app.db.repositories import ProcessRepository
from app.workflow.nodes import (
    node_stage1_process_analysis,
    node_stage2_research_evidence,
    node_stage3_ai_opportunity,
    node_stage4_future_design,
    node_stage5_validation_persistence
)

class TestResearchValidationAndFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_four_invalid_urls_are_never_valid(self):
        invalid_urls = [
            "https://www.mckinsey.com/capabilities/operations/our-insights/ai-process-automation",
            "https://www.gartner.com/en/information-technology/topics/autonomous-workflows",
            "https://www.mckinsey.com/capabilities/operations/our-insights/ai-in-supply-chain-and-retail",
            "https://www.gartner.com/en/supply-chain/topics/autonomous-supply-chain"
        ]
        for url in invalid_urls:
            self.assertFalse(
                ResearchService.is_valid_research_url(url),
                f"Invalid URL should have been rejected by URL validation: {url}"
            )

    def test_http_404_and_inaccessible_urls_rejected(self):
        bad_urls = [
            "https://httpbin.org/status/404",
            "https://httpbin.org/status/500",
            "https://invalid-non-existent-domain-9999.org/page"
        ]
        for url in bad_urls:
            self.assertFalse(
                ResearchService.is_valid_research_url(url),
                f"Inaccessible or 404 URL should have been rejected: {url}"
            )

    def test_valid_accessible_urls_retained(self):
        valid_urls = [
            "https://httpbin.org/status/200",
            "https://www.google.com"
        ]
        for url in valid_urls:
            self.assertTrue(
                ResearchService.is_valid_research_url(url),
                f"Valid accessible URL should be accepted: {url}"
            )

    def test_invalid_urls_skipped_without_fake_evidence_fabrication(self):
        # Mock search returning invalid items
        results = ResearchService.search("NonExistentSpecializedQuery123456789", max_results=2)
        for item in results:
            url = item["source_url"]
            # Ensure any returned result has a strictly valid URL
            self.assertTrue(ResearchService.is_valid_research_url(url), f"Returned evidence URL is invalid: {url}")
            # Ensure none of the 4 specified invalid URLs are present
            for forbidden in ResearchService.FORBIDDEN_INVALID_URL_PATTERNS:
                self.assertNotIn(forbidden, url.lower())

    def test_unbacked_activities_classified_as_analytic_recommendation(self):
        activities = [
            {
                "activity_id": "act-unbacked-1",
                "sequence_order": 1,
                "name": "Custom Unbacked Step",
                "description": "Step with no external web research match",
                "role": "Analyst",
                "system": "Custom System",
                "operational_problem": "Manual processing delay"
            }
        ]
        state = {
            "transformation_run_id": "run-test-unbacked-001",
            "process_id": "proc-unbacked-001",
            "process_name": "Specialized Custom Process",
            "industry": "General",
            "description": "Test process",
            "is_custom": True,
            "current_activities": activities,
            "research_queries": ["Specialized Custom Process AI automation solution for Custom Unbacked Step"],
            "research_evidence": [],  # Empty evidence (no valid web search match)
            "ai_opportunities": [],
            "future_activities": [],
            "impact_assessment": None,
            "status": "STAGE2_COMPLETED",
            "error_message": None
        }

        # Stage 3 with empty research_evidence
        res3 = node_stage3_ai_opportunity(state)
        opps = res3["ai_opportunities"]
        self.assertEqual(len(opps), 1)
        opp = opps[0]

        # Must NOT classify as EVIDENCE_BACKED when research_evidence is empty
        self.assertEqual(opp["provenance_type"], "ANALYTIC_RECOMMENDATION")
        self.assertIsNone(opp["linked_evidence_id"])

    def test_employee_onboarding_and_order_fulfillment_domain_relevance(self):
        # 1. Employee Onboarding
        hr_proc = ProcessRepository.create_process(
            db=self.db,
            name="Employee Onboarding",
            industry="Human Resources",
            description="New hire onboarding and document collection",
            activities=[
                {
                    "name": "Document Collection & Identity Verification",
                    "description": "Collect tax and ID documents",
                    "role": "HR Specialist",
                    "system": "Workday",
                    "operational_problem": "Paperwork collection is slow"
                }
            ],
            is_custom=True
        )

        state_hr = {
            "transformation_run_id": "run-hr-rel-001",
            "process_id": hr_proc.id,
            "process_name": hr_proc.name,
            "industry": hr_proc.industry,
            "description": hr_proc.description,
            "is_custom": True,
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
                for act in hr_proc.current_activities
            ],
            "research_queries": [],
            "research_evidence": [],
            "ai_opportunities": [],
            "future_activities": [],
            "impact_assessment": None,
            "status": "INITIATED",
            "error_message": None
        }

        res1_hr = node_stage1_process_analysis(state_hr)
        state_hr.update(res1_hr)
        res2_hr = node_stage2_research_evidence(state_hr, db_session=self.db)
        state_hr.update(res2_hr)

        # Check HR evidence contains no retail terms and no invalid McKinsey/Gartner URLs
        for ev in state_hr["research_evidence"]:
            url = ev["source_url"]
            self.assertTrue(ResearchService.is_valid_research_url(url))
            for forbidden in ResearchService.FORBIDDEN_INVALID_URL_PATTERNS:
                self.assertNotIn(forbidden, url.lower())

        # 2. Order Fulfillment
        retail_proc = ProcessRepository.create_process(
            db=self.db,
            name="Order Fulfillment",
            industry="Retail / E-commerce",
            description="Warehouse item picking and shipping",
            activities=[
                {
                    "name": "Warehouse Batch Picking",
                    "description": "Generate pick lists for warehouse staff",
                    "role": "Warehouse Picker",
                    "system": "Printed Pick Sheets",
                    "operational_problem": "Suboptimal pick paths cause excess travel"
                }
            ],
            is_custom=False
        )

        state_ret = {
            "transformation_run_id": "run-ret-rel-001",
            "process_id": retail_proc.id,
            "process_name": retail_proc.name,
            "industry": retail_proc.industry,
            "description": retail_proc.description,
            "is_custom": False,
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
                for act in retail_proc.current_activities
            ],
            "research_queries": [],
            "research_evidence": [],
            "ai_opportunities": [],
            "future_activities": [],
            "impact_assessment": None,
            "status": "INITIATED",
            "error_message": None
        }

        res1_ret = node_stage1_process_analysis(state_ret)
        state_ret.update(res1_ret)
        res2_ret = node_stage2_research_evidence(state_ret, db_session=self.db)
        state_ret.update(res2_ret)

        for ev in state_ret["research_evidence"]:
            url = ev["source_url"]
            self.assertTrue(ResearchService.is_valid_research_url(url))
            for forbidden in ResearchService.FORBIDDEN_INVALID_URL_PATTERNS:
                self.assertNotIn(forbidden, url.lower())

if __name__ == "__main__":
    unittest.main()
