"""Script to generate a reproducible 30-case golden dataset from real CSVs.

The golden dataset covers a diverse mix of:
- Rate bands: high (>300k), mid (200k-300k), low (<200k)
- Customer budget bands: high, mid, low
- Incumbent vs non-incumbent customers
"""

import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_FILE = Path(__file__).resolve().parent / "golden_dataset.json"


def get_latest_occupants(bookings_df: pd.DataFrame) -> dict:
    """Map each site_id to its most recent customer_id (incumbent)."""
    sorted_b = bookings_df.sort_values(by="end_date", ascending=True)
    incumbents = {}
    for _, row in sorted_b.iterrows():
        incumbents[str(row["site_id"]).strip()] = str(row["customer_id"]).strip()
    return incumbents


def calculate_rate_band(monthly_rate_inr: int) -> str:
    if monthly_rate_inr < 200000:
        return "low"
    elif monthly_rate_inr <= 300000:
        return "mid"
    return "high"


def build_golden_dataset(output_path: Path = OUTPUT_FILE) -> list:
    hoardings = pd.read_csv(DATA_DIR / "hoardings.csv")
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    bookings = pd.read_csv(DATA_DIR / "bookings.csv")

    hoardings["site_id"] = hoardings["site_id"].astype(str).str.strip()
    hoardings["location"] = hoardings["location"].astype(str).str.strip()
    hoardings["rate_band"] = hoardings["monthly_rate_inr"].apply(calculate_rate_band)

    customers["customer_id"] = customers["customer_id"].astype(str).str.strip()
    customers["name"] = customers["name"].astype(str).str.strip()
    customers["industry"] = customers["industry"].astype(str).str.strip()
    customers["budget_band"] = customers["budget_band"].astype(str).str.strip().str.lower()

    incumbents = get_latest_occupants(bookings)

    # Filter sites into rate tiers
    high_sites = hoardings[hoardings["rate_band"] == "high"].to_dict("records")
    mid_sites = hoardings[hoardings["rate_band"] == "mid"].to_dict("records")
    low_sites = hoardings[hoardings["rate_band"] == "low"].to_dict("records")

    cust_by_budget = {
        "high": customers[customers["budget_band"] == "high"].to_dict("records"),
        "mid": customers[customers["budget_band"] == "mid"].to_dict("records"),
        "low": customers[customers["budget_band"] == "low"].to_dict("records"),
    }

    cases = []
    seen_pairs = set()

    def add_case(site: dict, cust: dict, reason: str = ""):
        pair = (site["site_id"], cust["customer_id"])
        if pair in seen_pairs or len(cases) >= 30:
            return
        seen_pairs.add(pair)
        is_incumbent = incumbents.get(site["site_id"]) == cust["customer_id"]
        cases.append({
            "case_id": f"CASE_{len(cases) + 1:03d}",
            "site_id": site["site_id"],
            "customer_id": cust["customer_id"],
            "location": site["location"],
            "size_sqft": int(site["size_sqft"]),
            "traffic_score": float(site["traffic_score"]),
            "monthly_rate_inr": int(site["monthly_rate_inr"]),
            "rate_band": site["rate_band"],
            "customer_name": cust["name"],
            "industry": cust["industry"],
            "budget_band": cust["budget_band"],
            "is_incumbent": is_incumbent,
            "category": reason,
        })

    # 1. Incumbent cases (first priority)
    for site in hoardings.to_dict("records"):
        inc_id = incumbents.get(site["site_id"])
        if inc_id:
            cust_matches = customers[customers["customer_id"] == inc_id]
            if not cust_matches.empty:
                cust = cust_matches.iloc[0].to_dict()
                add_case(site, cust, "incumbent_renewal")
                if len(cases) >= 10:
                    break

    # 2. High rate sites with matching high budget customers
    for site in high_sites:
        for cust in cust_by_budget["high"]:
            add_case(site, cust, "high_rate_high_budget")

    # 3. High rate sites with mid budget customers (moderate stretch)
    for site in high_sites:
        for cust in cust_by_budget["mid"]:
            add_case(site, cust, "high_rate_mid_budget")

    # 4. Mid rate sites with mid budget customers
    for site in mid_sites:
        for cust in cust_by_budget["mid"]:
            add_case(site, cust, "mid_rate_mid_budget")

    # 5. Mid rate sites with high budget customers
    for site in mid_sites:
        for cust in cust_by_budget["high"]:
            add_case(site, cust, "mid_rate_high_budget")

    # 6. Mid rate sites with low budget customers
    for site in mid_sites:
        for cust in cust_by_budget["low"]:
            add_case(site, cust, "mid_rate_low_budget")

    # 7. Low rate sites with low budget customers
    for site in low_sites:
        for cust in cust_by_budget["low"]:
            add_case(site, cust, "low_rate_low_budget")

    # 8. Low rate sites with mid budget customers
    for site in low_sites:
        for cust in cust_by_budget["mid"]:
            add_case(site, cust, "low_rate_mid_budget")

    # 9. Low rate sites with high budget customers
    for site in low_sites:
        for cust in cust_by_budget["high"]:
            add_case(site, cust, "low_rate_high_budget")

    # Fill remaining up to 30 with any available valid combinations
    for site in hoardings.to_dict("records"):
        for cust in customers.to_dict("records"):
            if len(cases) >= 30:
                break
            add_case(site, cust, "general_portfolio_mix")
        if len(cases) >= 30:
            break

    cases = cases[:30]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)

    print(f"Generated {len(cases)} golden test cases to {output_path}")
    return cases


if __name__ == "__main__":
    build_golden_dataset()
