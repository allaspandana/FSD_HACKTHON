import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

TEMP_DB = Path(tempfile.gettempdir()) / "bugdiary_test_suite.db"
if TEMP_DB.exists():
    TEMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DB.as_posix()}"

from backend.main import app, Base, engine

class BugDiaryAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    def sample_payload(self, **overrides):
        data = {
            "title": "Loop boundary error", "language": "Python", "topic": "Loops",
            "error_message": "IndexError: list index out of range",
            "incorrect_code": "for i in range(len(items)+1): pass",
            "corrected_code": "for item in items: pass", "explanation": "Avoid the extra index.",
            "root_cause": "Incorrect range boundary", "difficulty": "Medium",
            "tags": "loops,indexing", "recorded_on": "2026-10-12", "next_revision": "2026-10-12"
        }
        data.update(overrides)
        return data

    def test_create_list_get_update_delete(self):
        response = self.client.post("/api/mistakes", json=self.sample_payload())
        self.assertEqual(response.status_code, 201)
        item_id = response.json()["id"]
        self.assertEqual(self.client.get("/api/mistakes").json()[0]["id"], item_id)
        self.assertEqual(self.client.get(f"/api/mistakes/{item_id}").status_code, 200)
        self.assertEqual(self.client.put(f"/api/mistakes/{item_id}", json={"title":"Updated loop bug"}).json()["title"], "Updated loop bug")
        self.assertEqual(self.client.delete(f"/api/mistakes/{item_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/mistakes/{item_id}").status_code, 404)

    def test_search_and_filter(self):
        self.client.post("/api/mistakes", json=self.sample_payload())
        self.client.post("/api/mistakes", json=self.sample_payload(title="Java syntax issue", language="Java", topic="Syntax", error_message="';' expected", tags="java,syntax"))
        self.assertEqual(len(self.client.get("/api/mistakes?search=IndexError").json()), 1)
        self.assertEqual(len(self.client.get("/api/mistakes?language=Java").json()), 1)
        self.assertEqual(len(self.client.get("/api/mistakes?tag=indexing").json()), 1)

    def test_revision_and_dashboard(self):
        item = self.client.post("/api/mistakes", json=self.sample_payload()).json()
        self.assertEqual(len(self.client.get("/api/mistakes?revision=due").json()), 1)
        self.client.post(f"/api/mistakes/{item['id']}/review", json={"note":"Reviewed"})
        self.assertEqual(len(self.client.get("/api/mistakes?revision=completed").json()), 1)
        dashboard = self.client.get("/api/dashboard").json()
        self.assertEqual(dashboard["total"], 1)
        self.assertEqual(dashboard["completed_reviews"], 1)

    def test_validation_and_not_found(self):
        self.assertEqual(self.client.post("/api/mistakes", json={"title":"x"}).status_code, 422)
        self.assertEqual(self.client.get("/api/mistakes/99999").status_code, 404)

if __name__ == "__main__":
    unittest.main()
