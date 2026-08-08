import pytest
from pathlib import Path
from app.data_loader import load_all_datasets
from app.scoring import calculate_lead_scores

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_hard_budget_constraint():
    """Verify that low budget customers are hard-disqualified for high rate sites."""
    hoardings, customers, bookings = load_all_datasets(DATA_DIR)
    ref_date = "2026-08-08"

    # HRD-106 is high rate band (₹400,000/mo)
    score_result = calculate_lead_scores(
        site_id="HRD-106",
        hoardings_df=hoardings,
        customers_df=customers,
        bookings_df=bookings,
        reference_date_str=ref_date,
        include_disqualified=True
    )

    leads = score_result["leads"]
    assert len(leads) > 0

    # Find CUST-34 (Apex Coaching - budget_band: low)
    low_budget_lead = next(l for l in leads if l["customer_id"] == "CUST-34")
    assert low_budget_lead["is_disqualified"] is True
    assert low_budget_lead["total_score"] == 0.0
    assert "Disqualified" in low_budget_lead["disqualification_reason"]
    assert len(low_budget_lead["reasons"]) > 0

    # Top leads for HRD-106 MUST NOT be disqualified
    top_lead = leads[0]
    assert top_lead["is_disqualified"] is False
    assert top_lead["total_score"] > 0


def test_explicit_reasons_and_breakdown():
    """Verify that every scored lead contains explicit human-readable reasons and score breakdown."""
    hoardings, customers, bookings = load_all_datasets(DATA_DIR)
    ref_date = "2026-08-08"

    score_result = calculate_lead_scores(
        site_id="HRD-106",
        hoardings_df=hoardings,
        customers_df=customers,
        bookings_df=bookings,
        reference_date_str=ref_date
    )

    leads = score_result["leads"]
    for lead in leads:
        assert isinstance(lead["reasons"], list)
        assert len(lead["reasons"]) > 0
        assert "site_history" in lead["breakdown"]
        assert "budget_fit" in lead["breakdown"]
        assert "industry_fit" in lead["breakdown"]


def test_incumbent_customer_flagging():
    """Verify that the current occupant of a site is flagged as incumbent."""
    hoardings, customers, bookings = load_all_datasets(DATA_DIR)
    ref_date = "2026-08-08"

    # HRD-106 incumbent occupant is CUST-32 (GreenLeaf Realty)
    score_result = calculate_lead_scores(
        site_id="HRD-106",
        hoardings_df=hoardings,
        customers_df=customers,
        bookings_df=bookings,
        reference_date_str=ref_date
    )

    incumbent_lead = next(l for l in score_result["leads"] if l["customer_id"] == "CUST-32")
    assert incumbent_lead["incumbent_status"] is True
    assert any("CURRENT INCUMBENT" in r for r in incumbent_lead["reasons"])
