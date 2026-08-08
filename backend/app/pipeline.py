from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict, Any, Optional


def get_upcoming_vacancies(
    hoardings_df: pd.DataFrame,
    bookings_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    reference_date_str: Optional[str] = None,
    max_days: int = 90
) -> List[Dict[str, Any]]:
    """
    Detects upcoming site vacancies ending within the next max_days (default 90 days).
    
    A site counts as an upcoming vacancy if:
    1. Its latest booking end_date falls within [reference_date, reference_date + max_days]
       (or is already past), AND
    2. There is no subsequent follow-on booking starting after that end_date.
    
    free_from = end_date + 1 day.
    """
    if reference_date_str:
        ref_date = pd.to_datetime(reference_date_str).date()
    else:
        # Default to current date (2026-08-08)
        ref_date = datetime.now().date()

    window_end = ref_date + timedelta(days=max_days)

    customer_map = dict(zip(customers_df["customer_id"], customers_df["name"]))
    vacancies = []

    for _, hoarding in hoardings_df.iterrows():
        site_id = hoarding["site_id"]
        site_bookings = bookings_df[bookings_df["site_id"] == site_id].copy()

        if site_bookings.empty:
            # Site has never been booked - available immediately
            vacancies.append({
                "site_id": site_id,
                "location": hoarding["location"],
                "size_sqft": int(hoarding["size_sqft"]),
                "traffic_score": float(hoarding["traffic_score"]),
                "monthly_rate_inr": int(hoarding["monthly_rate_inr"]),
                "rate_band": hoarding["rate_band"],
                "end_date": ref_date.strftime("%Y-%m-%d"),
                "free_from": ref_date.strftime("%Y-%m-%d"),
                "days_until_vacant": 0,
                "current_occupant_id": None,
                "current_occupant_name": None,
                "revenue_at_risk": int(hoarding["monthly_rate_inr"])
            })
            continue

        site_bookings["end_dt"] = pd.to_datetime(site_bookings["end_date"]).dt.date
        site_bookings["start_dt"] = pd.to_datetime(site_bookings["start_date"]).dt.date
        site_bookings = site_bookings.sort_values(by="end_dt", ascending=True)

        latest_booking = site_bookings.iloc[-1]
        latest_end_dt = latest_booking["end_dt"]

        # Check if there is any follow-on booking starting after latest_end_dt
        future_bookings = site_bookings[site_bookings["start_dt"] > latest_end_dt]
        if not future_bookings.empty:
            # Follow-on booking exists, so site is not falling vacant after latest_end_dt
            continue

        # Also check if there is an active booking covering past ref_date + max_days
        active_long_bookings = site_bookings[site_bookings["end_dt"] > window_end]
        if not active_long_bookings.empty:
            # Site booked beyond 90 days - do not include
            continue

        # Check if latest end date is within [ref_date, window_end] or in past
        if latest_end_dt <= window_end:
            if latest_end_dt >= ref_date:
                free_from_dt = latest_end_dt + timedelta(days=1)
                days_until = max(0, (free_from_dt - ref_date).days)
            else:
                # Already ended in past
                free_from_dt = ref_date
                days_until = 0

            occupant_id = latest_booking["customer_id"]
            occupant_name = customer_map.get(occupant_id, "Unknown Customer")

            vacancies.append({
                "site_id": site_id,
                "location": hoarding["location"],
                "size_sqft": int(hoarding["size_sqft"]),
                "traffic_score": float(hoarding["traffic_score"]),
                "monthly_rate_inr": int(hoarding["monthly_rate_inr"]),
                "rate_band": hoarding["rate_band"],
                "end_date": latest_end_dt.strftime("%Y-%m-%d"),
                "free_from": free_from_dt.strftime("%Y-%m-%d"),
                "days_until_vacant": days_until,
                "current_occupant_id": occupant_id,
                "current_occupant_name": occupant_name,
                "revenue_at_risk": int(hoarding["monthly_rate_inr"])
            })

    # Sort vacancies by days_until_vacant ascending
    vacancies.sort(key=lambda x: x["days_until_vacant"])
    return vacancies
