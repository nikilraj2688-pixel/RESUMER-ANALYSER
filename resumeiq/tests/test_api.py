import pytest
import io
import os
from resumeiq.app import create_app
from resumeiq.app.config import TestingConfig

@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"

def test_roles_endpoint(client):
    res = client.get("/api/roles")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_count"] >= 20

def test_analyze_endpoint(client):
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_swe.docx")
    with open(fixture_path, "rb") as f:
        file_bytes = f.read()

    data = {
        "file": (io.BytesIO(file_bytes), "sample_swe.docx")
    }

    res = client.post("/api/analyze", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    json_data = res.get_json()
    assert "role_prediction" in json_data
    assert "best_fit_role" in json_data["role_prediction"]
    assert "ats_score" in json_data
    assert "skill_gap_analysis" in json_data

