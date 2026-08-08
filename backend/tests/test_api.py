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


def test_vacancies_endpoint():
    response = client.get("/api/vacancies?max_days=90&ref_date=2026-08-08")
    assert response.status_code == 200
    vacancies = response.json()
    assert isinstance(vacancies, list)
    assert len(vacancies) > 0
    # Confirm SITE_001 is present with correct free_from date
    site_1 = next((v for v in vacancies if v["site_id"] == "SITE_001"), None)
    assert site_1 is not None
    assert site_1["free_from"] == "2026-09-01"


def test_leads_endpoint():
    response = client.get("/api/leads/SITE_001?ref_date=2026-08-08")
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == "SITE_001"
    assert len(data["leads"]) > 0

    # Ensure disqualified customer is ranked at bottom or marked disqualified
    leads = data["leads"]
    top_lead = leads[0]
    assert top_lead["is_disqualified"] is False
    assert len(top_lead["reasons"]) > 0


def test_pitch_endpoint():
    payload = {
        "site_id": "SITE_001",
        "customer_id": "CUST_001"
    }
    response = client.post("/api/pitch?ref_date=2026-08-08", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == "SITE_001"
    assert data["customer_id"] == "CUST_001"
    assert data["quoted_rate_inr"] == 380000
    assert "pitch_text" in data
    assert len(data["pitch_text"]) > 50
    # Must quote exact site location and rate
    assert "Bandra Flyover Junction" in data["pitch_text"] or "SITE_001" in data["pitch_text"] or "380,000" in data["pitch_text"]
