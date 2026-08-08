import pytest
from pathlib import Path
from app.data_loader import load_all_datasets
from app.pipeline import get_upcoming_vacancies

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def test_vacancies_90_day_filter():
    """Verify that vacancies only include sites ending within 90 days and no follow-on bookings."""
    hoardings, customers, bookings = load_all_datasets(DATA_DIR)
    ref_date = "2026-08-08"

    vacancies = get_upcoming_vacancies(
        hoardings_df=hoardings,
        bookings_df=bookings,
        customers_df=customers,
        reference_date_str=ref_date,
        max_days=90
    )

    assert len(vacancies) > 0

    vacant_site_ids = [v["site_id"] for v in vacancies]

    # SITE_001 ends 2026-08-31 (in 23 days) -> MUST be included
    assert "SITE_001" in vacant_site_ids
    site_1_vac = next(v for v in vacancies if v["site_id"] == "SITE_001")
    assert site_1_vac["free_from"] == "2026-09-01"

    # SITE_004 ends 2026-08-15 BUT has follow-on booking starting 2026-08-16 -> MUST NOT be included
    assert "SITE_004" not in vacant_site_ids

    # SITE_010 booking ends 2026-12-31 (> 90 days) -> MUST NOT be included
    assert "SITE_010" not in vacant_site_ids

    # Verify every vacancy has days_until_vacant <= 90
    for vac in vacancies:
        assert vac["days_until_vacant"] <= 90
        assert vac["free_from"] > vac["end_date"] or vac["days_until_vacant"] == 0
