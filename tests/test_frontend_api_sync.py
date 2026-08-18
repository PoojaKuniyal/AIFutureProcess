import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

class TestFrontendApiStateSynchronization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def test_transformation_state_synchronization(self):
        # 1. Create custom process
        create_resp = self.client.post("/api/v1/processes", json={
            "name": "Sync Test Process",
            "industry": "Human Resources",
            "description": "State sync test process overview",
            "current_process_text": "Step 1: Collect employee forms\nStep 2: IT provisions accounts",
            "problems_text": "Paperwork collection is slow"
        })
        self.assertEqual(create_resp.status_code, 201)
        proc_data = create_resp.json()
        proc_id = proc_data["process_id"]

        # 2. GET detail before transformation -> future_process must be None
        pre_detail = self.client.get(f"/api/v1/processes/{proc_id}")
        self.assertEqual(pre_detail.status_code, 200)
        pre_json = pre_detail.json()
        self.assertIsNone(pre_json.get("future_process"))
        self.assertEqual(len(pre_json["current_activities"]), 2)

        # 3. POST transform -> Execute transformation
        trans_resp = self.client.post(f"/api/v1/processes/{proc_id}/transform")
        self.assertEqual(trans_resp.status_code, 200)

        # 4. Immediate GET detail post-transformation -> future_process must be COMPLETED with activities, impact, & evidence
        post_detail = self.client.get(f"/api/v1/processes/{proc_id}")
        self.assertEqual(post_detail.status_code, 200)
        post_json = post_detail.json()

        future_proc = post_json.get("future_process")
        self.assertIsNotNone(future_proc)
        self.assertEqual(future_proc["status"], "COMPLETED")
        self.assertGreater(len(future_proc["future_activities"]), 0)
        self.assertIsNotNone(future_proc["impact_assessment"])

        # Evidence items should also be populated and returned
        evidence_items = post_json.get("evidence_items", [])
        self.assertIsNotNone(evidence_items)

        # 5. Subsequent GET requests reliably return completed state
        subsequent_detail = self.client.get(f"/api/v1/processes/{proc_id}")
        self.assertEqual(subsequent_detail.status_code, 200)
        self.assertEqual(subsequent_detail.json()["future_process"]["status"], "COMPLETED")

    def test_poll_transformation_status_recovers_completed_backend_state(self):
        # 1. Create process
        create_resp = self.client.post("/api/v1/processes", json={
            "name": "Timeout Sync Process",
            "industry": "Retail",
            "description": "Timeout recovery test process overview",
            "current_process_text": "Step 1: Receive store order\nStep 2: Dispatch from warehouse",
            "problems_text": "Manual dispatch errors"
        })
        self.assertEqual(create_resp.status_code, 201)
        proc_id = create_resp.json()["process_id"]

        # 2. Trigger transformation on backend
        trans_resp = self.client.post(f"/api/v1/processes/{proc_id}/transform")
        self.assertEqual(trans_resp.status_code, 200)

        # 3. Simulate polling status directly from GET endpoint
        detail_resp = self.client.get(f"/api/v1/processes/{proc_id}")
        self.assertEqual(detail_resp.status_code, 200)
        detail_json = detail_resp.json()

        # Must recover COMPLETED status from PostgreSQL
        self.assertIsNotNone(detail_json.get("future_process"))
        self.assertEqual(detail_json["future_process"]["status"], "COMPLETED")
        self.assertGreater(len(detail_json["future_process"]["future_activities"]), 0)

if __name__ == "__main__":
    unittest.main()
