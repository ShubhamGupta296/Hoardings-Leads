import os
import json
import httpx
import pandas as pd
from typing import Dict, Any, Optional

from app.scoring import calculate_lead_scores


def generate_templated_pitch(
    site: pd.Series,
    customer: pd.Series,
    reasons: list,
    incumbent_status: bool
) -> str:
    """Generates a high-converting, grounded sales pitch using dynamic templating."""
    site_location = site["location"]
    size_sqft = site["size_sqft"]
    traffic_score = site["traffic_score"]
    rate_inr = int(site["monthly_rate_inr"])
    cust_name = customer["name"]
    cust_industry = customer["industry"]

    reason_highlights = "\n".join([f"- {r}" for r in reasons[:3]])

    if incumbent_status:
        opening = f"Dear {cust_name} Team,\n\nWe value our ongoing partnership with your brand."
        angle = f"As your current campaign at **{site_location}** approaches its renewal window, we are reserving priority first-right-of-refusal for {cust_name} before opening this high-impact hoarding to market bidders."
    else:
        opening = f"Dear {cust_name} Sales & Marketing Team,\n\nI am reaching out from Hoardings Inc with an exclusive prime OOH media site tailored for {cust_industry} dominance."
        angle = f"Our upcoming premium hoarding site at **{site_location}** is coming vacant soon and represents a perfect strategic fit for {cust_name}."

    pitch_body = f"""{opening}

{angle}

### Key Site Specifications (Verified Rate Card):
- **Location:** {site_location}
- **Display Size:** {size_sqft:,} sq. ft.
- **Traffic Rating:** {traffic_score}/10 High-Density Eyeball Score
- **Monthly Rate:** ₹{rate_inr:,} / month (Fixed Rate Card)

### Why This Location is Ideal for {cust_name}:
{reason_highlights}

Given the exceptionally high traffic flow of {traffic_score}/10 at {site_location}, securing this premium space will deliver massive daily impressions for {cust_name}'s campaigns in the upcoming quarter.

Would you be available for a brief 5-minute call this week to lock in this inventory rate of ₹{rate_inr:,}/month before public release?

Warm regards,

**Sales Leadership Team**  
Smart Leads Agent | Hoardings Inc.
"""
    return pitch_body.strip()


def generate_pitch(
    site_id: str,
    customer_id: str,
    hoardings_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    bookings_df: pd.DataFrame,
    reference_date_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a personalized pitch using Claude API if ANTHROPIC_API_KEY is configured,
    otherwise gracefully falls back to the template pitch generator.
    """
    site_rows = hoardings_df[hoardings_df["site_id"] == site_id]
    if site_rows.empty:
        raise ValueError(f"Site ID {site_id} not found.")
    site = site_rows.iloc[0]

    cust_rows = customers_df[customers_df["customer_id"] == customer_id]
    if cust_rows.empty:
        raise ValueError(f"Customer ID {customer_id} not found.")
    customer = cust_rows.iloc[0]

    # Get scoring details & reasons
    score_result = calculate_lead_scores(site_id, hoardings_df, customers_df, bookings_df, reference_date_str)
    lead_data = next((l for l in score_result["leads"] if l["customer_id"] == customer_id), None)

    reasons = lead_data["reasons"] if lead_data else ["Matches targeted demographic traffic."]
    incumbent_status = lead_data["incumbent_status"] if lead_data else False
    total_score = lead_data["total_score"] if lead_data else 50.0

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    generated_by_ai = False
    pitch_text = ""

    grounding_facts = {
        "site_id": site_id,
        "location": site["location"],
        "size_sqft": int(site["size_sqft"]),
        "traffic_score": float(site["traffic_score"]),
        "monthly_rate_inr": int(site["monthly_rate_inr"]),
        "customer_id": customer_id,
        "customer_name": customer["name"],
        "industry": customer["industry"],
        "budget_band": customer["budget_band"],
        "lead_score": total_score,
        "incumbent_status": incumbent_status
    }

    if api_key:
        try:
            # Call Claude API via httpx synchronous/http call
            prompt = f"""You are a professional out-of-home (OOH) media sales lead generator.
Write a personalized, highly persuasive B2B sales email pitch for an upcoming billboard/hoarding site vacancy.

STRICT GROUNDING CONSTRAINTS:
- You MUST quote the EXACT monthly rate: ₹{int(site['monthly_rate_inr']):,}/month. NEVER change or invent prices.
- You MUST mention the EXACT site location: {site['location']}.
- You MUST mention the EXACT display size: {int(site['size_sqft'])} sq. ft.
- Target Customer: {customer['name']} (Industry: {customer['industry']})
- Fit score: {total_score}/100
- Incumbent status: {incumbent_status}
- Key data-backed reasons to include:
{json.dumps(reasons, indent=2)}

Keep the email professional, persuasive, concise (under 250 words), and end with a clear call-to-action to lock in the site rate."""

            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=15.0
            )

            if response.status_code == 200:
                resp_json = response.json()
                content = resp_json.get("content", [])
                if content and len(content) > 0:
                    pitch_text = content[0].get("text", "").strip()
                    generated_by_ai = True
        except Exception:
            # Fallback to templated pitch on API error
            generated_by_ai = False

    if not pitch_text:
        pitch_text = generate_templated_pitch(site, customer, reasons, incumbent_status)

    return {
        "site_id": site_id,
        "customer_id": customer_id,
        "site_location": site["location"],
        "customer_name": customer["name"],
        "quoted_rate_inr": int(site["monthly_rate_inr"]),
        "pitch_text": pitch_text,
        "generated_by_ai": generated_by_ai,
        "grounding_facts": grounding_facts
    }
