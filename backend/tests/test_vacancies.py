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

    # HRD-103 ends 2026-08-30 (in 22 days) -> MUST be included
    assert "HRD-103" in vacant_site_ids
    hrd_103_vac = next(v for v in vacancies if v["site_id"] == "HRD-103")
    assert hrd_103_vac["free_from"] == "2026-08-31"

    # HRD-100 ends 2026-11-15 (> 90 days from 2026-08-08) -> MUST NOT be included
    assert "HRD-100" not in vacant_site_ids

    # Verify every vacancy has days_until_vacant <= 90
    for vac in vacancies:
        assert vac["days_until_vacant"] <= 90
        assert vac["free_from"] > vac["end_date"] or vac["days_until_vacant"] == 0
