import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["datasets"]["hoardings_count"] == 25
    assert data["datasets"]["customers_count"] == 20


def test_vacancies_endpoint():
    response = client.get("/api/vacancies?max_days=90&ref_date=2026-08-08")
    assert response.status_code == 200
    vacancies = response.json()
    assert isinstance(vacancies, list)
    assert len(vacancies) > 0
    # Confirm HRD-103 is present with free_from date 2026-08-31
    hrd_103 = next((v for v in vacancies if v["site_id"] == "HRD-103"), None)
    assert hrd_103 is not None
    assert hrd_103["free_from"] == "2026-08-31"


def test_leads_endpoint():
    response = client.get("/api/leads/HRD-106?ref_date=2026-08-08")
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == "HRD-106"
    assert len(data["leads"]) == 20

    # Ensure top lead is qualified
    leads = data["leads"]
    top_lead = leads[0]
    assert top_lead["is_disqualified"] is False
    assert len(top_lead["reasons"]) > 0


def test_pitch_endpoint():
    payload = {
        "site_id": "HRD-106",
        "customer_id": "CUST-32"
    }
    response = client.post("/api/pitch?ref_date=2026-08-08", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == "HRD-106"
    assert data["customer_id"] == "CUST-32"
    assert data["quoted_rate_inr"] == 400000
    assert "pitch_text" in data
    assert len(data["pitch_text"]) > 50
    # Must quote site location and rate
    assert "Thane Ghodbunder" in data["pitch_text"] or "400,000" in data["pitch_text"]
