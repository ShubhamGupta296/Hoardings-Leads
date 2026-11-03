"""FastAPI TestClient endpoint and validation tests for Smart Leads Agent API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify system health and CSV dataset row counts."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["datasets"]["hoardings_count"] == 25
    assert data["datasets"]["customers_count"] == 20
    assert data["datasets"]["bookings_count"] == 49


def test_vacancies_endpoint_schema_and_window():
    """Verify vacancies response schema and strict 90-day window enforcement."""
    response = client.get("/api/vacancies?max_days=90&ref_date=2026-08-08")
    assert response.status_code == 200
    vacancies = response.json()
    assert isinstance(vacancies, list)
    assert len(vacancies) > 0

    required_keys = {
        "site_id",
        "location",
        "size_sqft",
        "traffic_score",
        "monthly_rate_inr",
        "rate_band",
        "end_date",
        "free_from",
        "days_until_vacant",
        "current_occupant_id",
        "current_occupant_name",
    }

    for vac in vacancies:
        assert required_keys.issubset(set(vac.keys()))
        # Rule: No vacancy beyond 90 days window
        assert vac["days_until_vacant"] <= 90
        assert vac["monthly_rate_inr"] > 0
        assert vac["rate_band"] in ["low", "mid", "high"]


def test_leads_endpoint_schema_and_reasons():
    """Verify leads endpoint response structure and non-empty reasons rule."""
    response = client.get("/api/leads/HRD-106?ref_date=2026-08-08")
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == "HRD-106"
    assert "leads" in data
    assert data["leads_count"] > 0

    lead_keys = {
        "customer_id",
        "customer_name",
        "industry",
        "budget_band",
        "relationship_score",
        "last_contact_date",
        "total_score",
        "is_disqualified",
        "breakdown",
        "reasons",
        "incumbent_status",
    }

    for lead in data["leads"]:
        assert lead_keys.issubset(set(lead.keys()))
        # Rule: Every lead must have explicit non-empty reasons explaining the score
        assert isinstance(lead["reasons"], list)
        assert len(lead["reasons"]) > 0


def test_hard_budget_constraint_disqualification():
    """Rule: A low-budget customer must be disqualified on a high-rate site."""
    # HRD-106 is a high-rate site (₹400,000/mo)
    resp_with_disq = client.get("/api/leads/HRD-106?include_disqualified=true&ref_date=2026-08-08")
    assert resp_with_disq.status_code == 200
    all_leads = resp_with_disq.json()["leads"]

    # CUST-34 (Apex Coaching, low budget) must be hard-disqualified with score = 0
    cust_34 = next((l for l in all_leads if l["customer_id"] == "CUST-34"), None)
    assert cust_34 is not None
    assert cust_34["is_disqualified"] is True
    assert cust_34["total_score"] == 0.0
    assert cust_34["disqualification_reason"] is not None

    # When include_disqualified=false, low-budget customers must not be returned
    resp_without_disq = client.get("/api/leads/HRD-106?include_disqualified=false&ref_date=2026-08-08")
    assert resp_without_disq.status_code == 200
    filtered_leads = resp_without_disq.json()["leads"]
    assert not any(l["customer_id"] == "CUST-34" for l in filtered_leads)
    assert all(not l["is_disqualified"] for l in filtered_leads)


def test_pitch_endpoint_schema():
    """Verify POST /api/pitch schema, grounded facts, and rate match."""
    payload = {
        "site_id": "HRD-106",
        "customer_id": "CUST-38"
    }
    response = client.post("/api/pitch?ref_date=2026-08-08", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["site_id"] == "HRD-106"
    assert data["customer_id"] == "CUST-38"
    assert data["quoted_rate_inr"] == 400000
    assert "pitch_text" in data
    assert len(data["pitch_text"]) > 50

    facts = data["grounding_facts"]
    assert facts["site_id"] == "HRD-106"
    assert facts["monthly_rate_inr"] == 400000
    assert facts["customer_id"] == "CUST-38"


def test_404_unknown_site_leads():
    """Verify 404 response for non-existent site ID."""
    response = client.get("/api/leads/NONEXISTENT_SITE_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_404_unknown_site_pitch():
    """Verify 404 response when generating pitch for invalid site ID."""
    payload = {
        "site_id": "NONEXISTENT_SITE_999",
        "customer_id": "CUST-38"
    }
    response = client.post("/api/pitch", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_404_unknown_customer_pitch():
    """Verify 404 response when generating pitch for invalid customer ID."""
    payload = {
        "site_id": "HRD-106",
        "customer_id": "NONEXISTENT_CUST_999"
    }
    response = client.post("/api/pitch", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
