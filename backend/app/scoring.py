from datetime import datetime
import pandas as pd
from typing import List, Dict, Any, Optional

BAND_LEVELS = {
    "low": 1,
    "mid": 2,
    "high": 3
}


def calculate_lead_scores(
    site_id: str,
    hoardings_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    bookings_df: pd.DataFrame,
    reference_date_str: Optional[str] = None,
    include_disqualified: bool = True
) -> Dict[str, Any]:
    """
    Ranks customers for a given site_id using 6 weighted factors and hard budget disqualification.
    
    Hard Constraint:
    If site rate band is 'high' and customer budget band is 'low' (gap >= 2), the customer
    is hard-disqualified (total_score = 0) and cannot appear at the top.
    
    Returns site info and ranked list of lead dictionaries with explicit reasons.
    """
    if reference_date_str:
        ref_date = pd.to_datetime(reference_date_str).date()
    else:
        ref_date = datetime.now().date()

    # Get target site
    site_rows = hoardings_df[hoardings_df["site_id"] == site_id]
    if site_rows.empty:
        raise ValueError(f"Site ID {site_id} not found in hoardings dataset.")

    site = site_rows.iloc[0]
    site_rate_inr = int(site["monthly_rate_inr"])
    site_rate_band = site["rate_band"]
    site_rate_level = BAND_LEVELS.get(site_rate_band, 2)

    # Infer historical industries for THIS specific site from past bookings
    site_past_bookings = bookings_df[bookings_df["site_id"] == site_id]
    past_customer_ids = site_past_bookings["customer_id"].unique()
    historical_customers = customers_df[customers_df["customer_id"].isin(past_customer_ids)]
    historical_industries = list(historical_customers["industry"].unique()) if not historical_customers.empty else []

    # Get latest occupant for incumbent identification
    latest_occupant_id = None
    if not site_past_bookings.empty:
        site_past_bookings_sorted = site_past_bookings.copy()
        site_past_bookings_sorted["end_dt"] = pd.to_datetime(site_past_bookings_sorted["end_date"]).dt.date
        site_past_bookings_sorted = site_past_bookings_sorted.sort_values(by="end_dt", ascending=True)
        latest_occupant_id = site_past_bookings_sorted.iloc[-1]["customer_id"]

    scored_leads = []

    for _, customer in customers_df.iterrows():
        cust_id = customer["customer_id"]
        cust_name = customer["name"]
        cust_industry = customer["industry"]
        cust_budget_band = customer["budget_band"]
        cust_budget_level = BAND_LEVELS.get(cust_budget_band, 1)
        rel_score = int(customer["relationship_score"])
        last_contact_str = customer["last_contact_date"]

        reasons = []

        # Check Hard Constraint: Budget Gap >= 2
        budget_gap = site_rate_level - cust_budget_level
        is_disqualified = False
        disqualification_reason = None

        if budget_gap >= 2:
            is_disqualified = True
            disqualification_reason = (
                f"Disqualified: Customer budget band ('{cust_budget_band}') is 2 levels below "
                f"site rate band ('{site_rate_band}' - ₹{site_rate_inr:,}/mo). Cannot realistically afford."
            )
            reasons.append(disqualification_reason)
            total_score = 0.0
            breakdown = {
                "site_history": 0.0,
                "total_history": 0.0,
                "budget_fit": 0.0,
                "industry_fit": 0.0,
                "relationship": 0.0,
                "contact_recency": 0.0
            }
        else:
            # 1. Site History (Max 25 pts)
            cust_site_bookings = site_past_bookings[site_past_bookings["customer_id"] == cust_id]
            site_booking_count = len(cust_site_bookings)
            if site_booking_count >= 2:
                site_hist_score = 25.0
                reasons.append(f"Strong site history: Booked this exact location ({site['location']}) {site_booking_count} times previously.")
            elif site_booking_count == 1:
                site_hist_score = 18.0
                reasons.append(f"Previous occupant: Booked this exact site 1 time in the past.")
            else:
                site_hist_score = 0.0

            # 2. Total History (Max 15 pts)
            all_cust_bookings = bookings_df[bookings_df["customer_id"] == cust_id]
            total_booking_count = len(all_cust_bookings)
            if total_booking_count >= 4:
                total_hist_score = 15.0
                reasons.append(f"Key corporate account: {total_booking_count} total historical bookings across our network.")
            elif total_booking_count in [2, 3]:
                total_hist_score = 10.0
                reasons.append(f"Repeat customer: {total_booking_count} total past bookings across our hoardings network.")
            elif total_booking_count == 1:
                total_hist_score = 5.0
                reasons.append(f"Existing client: 1 past booking with our agency.")
            else:
                total_hist_score = 0.0

            # 3. Budget Fit (Max 20 pts)
            if cust_budget_level >= site_rate_level:
                budget_score = 20.0
                reasons.append(f"Budget alignment: Customer budget band ('{cust_budget_band}') matches/exceeds site rate (₹{site_rate_inr:,}/month - '{site_rate_band}').")
            elif budget_gap == 1:
                budget_score = 10.0
                reasons.append(f"Moderate budget stretch: Customer budget band is '{cust_budget_band}' vs site rate band '{site_rate_band}' (₹{site_rate_inr:,}/month).")
            else:
                budget_score = 0.0

            # 4. Industry Fit (Max 20 pts)
            if historical_industries:
                if cust_industry in historical_industries:
                    # High volume check
                    ind_booking_count = len(site_past_bookings[
                        site_past_bookings["customer_id"].isin(
                            customers_df[customers_df["industry"] == cust_industry]["customer_id"]
                        )
                    ])
                    industry_score = 20.0
                    reasons.append(
                        f"Proven industry fit: '{cust_industry}' is a proven top occupant industry for this location "
                        f"({ind_booking_count} past bookings)."
                    )
                else:
                    industry_score = 8.0
                    reasons.append(f"New industry segment: '{cust_industry}' expansion candidate for this site location.")
            else:
                # Default industry score if no site history
                industry_score = 12.0
                reasons.append(f"Industry profile: High-visibility site suitable for '{cust_industry}' brand reach.")

            # 5. Relationship Score (Max 10 pts)
            rel_pts = min(10.0, float(rel_score))
            reasons.append(f"Relationship strength: Score of {rel_score}/10 with sales management.")

            # 6. Contact Recency (Max 10 pts)
            last_contact_dt = pd.to_datetime(last_contact_str).date()
            days_since_contact = max(0, (ref_date - last_contact_dt).days)
            if days_since_contact <= 15:
                recency_score = 10.0
                reasons.append(f"Active dialogue: Contacted recently ({days_since_contact} days ago on {last_contact_str}).")
            elif days_since_contact <= 30:
                recency_score = 8.0
                reasons.append(f"Recent engagement: Contacted {days_since_contact} days ago.")
            elif days_since_contact <= 60:
                recency_score = 5.0
                reasons.append(f"Warm lead: Last contacted {days_since_contact} days ago.")
            else:
                recency_score = 2.0
                reasons.append(f"Cold outreach required: Last contacted {days_since_contact} days ago.")

            breakdown = {
                "site_history": site_hist_score,
                "total_history": total_hist_score,
                "budget_fit": budget_score,
                "industry_fit": industry_score,
                "relationship": rel_pts,
                "contact_recency": recency_score
            }

            total_score = round(sum(breakdown.values()), 1)

        # Incumbent check
        is_incumbent = (cust_id == latest_occupant_id)
        if is_incumbent:
            reasons.insert(0, f"CURRENT INCUMBENT: Currently occupying {site_id} — prime renewal candidate before site opens to market!")

        lead_dict = {
            "customer_id": cust_id,
            "customer_name": cust_name,
            "industry": cust_industry,
            "budget_band": cust_budget_band,
            "relationship_score": rel_score,
            "last_contact_date": last_contact_str,
            "total_score": total_score,
            "is_disqualified": is_disqualified,
            "disqualification_reason": disqualification_reason,
            "breakdown": breakdown,
            "reasons": reasons,
            "incumbent_status": is_incumbent
        }

        scored_leads.append(lead_dict)

    # Sort leads: non-disqualified by total_score descending, disqualified at bottom
    scored_leads.sort(key=lambda x: (not x["is_disqualified"], x["total_score"]), reverse=True)

    if not include_disqualified:
        scored_leads = [l for l in scored_leads if not l["is_disqualified"]]

    return {
        "site_id": site_id,
        "location": site["location"],
        "monthly_rate_inr": site_rate_inr,
        "rate_band": site_rate_band,
        "leads_count": len(scored_leads),
        "leads": scored_leads
    }
