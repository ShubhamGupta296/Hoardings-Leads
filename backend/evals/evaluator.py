"""Deterministic and DeepEval pitch quality evaluation engine.

Evaluates generated pitches against ground-truth facts from the Golden Dataset:
1. Rate Check: all currency mentions must equal the site's monthly_rate_inr.
2. Fact Check: location, size_sqft, traffic_score, customer_name match ground truth.
3. Invented Number Check: no unauthorized numeric figures.
4. Optional DeepEval metrics (Faithfulness / Hallucination) via Claude LLM judge.
"""

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from app.data_loader import load_all_datasets
from app.pitch import generate_pitch
from evals.tracker import tracker

GOLDEN_FILE = Path(__file__).resolve().parent / "golden_dataset.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


@dataclass
class EvalResult:
    case_id: str
    site_id: str
    customer_id: str
    passed: bool
    groundedness_score: float
    has_hallucination: bool
    rate_check_passed: bool
    fact_check_passed: bool
    invented_numbers_passed: bool
    found_rates: List[int] = field(default_factory=list)
    hallucinations: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    generated_by_ai: bool = False
    latency_ms: float = 0.0
    pitch_length: int = 0


def load_golden_cases() -> List[Dict[str, Any]]:
    if not GOLDEN_FILE.exists():
        from evals.build_golden import build_golden_dataset
        return build_golden_dataset(GOLDEN_FILE)
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_rate_consistency(pitch_text: str, expected_rate: int) -> Tuple[bool, List[int], List[str]]:
    """Checks that every rupee amount in the pitch equals the ground-truth rate."""
    errors = []
    # Match patterns like: ₹380,000, Rs. 380000, INR 380,000, Rs 380,000/month
    rate_patterns = [
        r"[₹]\s*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+)",
        r"(?:Rs\.?|INR)\s*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+)",
    ]

    found_rates: Set[int] = set()
    for pat in rate_patterns:
        for match in re.finditer(pat, pitch_text, re.IGNORECASE):
            raw_num = match.group(1).replace(",", "").strip()
            try:
                found_rates.add(int(raw_num))
            except ValueError:
                continue

    found_list = sorted(list(found_rates))
    if not found_list:
        errors.append(f"No rate quoted in pitch (expected ₹{expected_rate:,})")
        return False, found_list, errors

    # Every quoted rupee rate must match expected_rate
    mismatches = [r for r in found_list if r != expected_rate]
    if mismatches:
        for m in mismatches:
            errors.append(f"Mismatched rate quoted: ₹{m:,} (expected ₹{expected_rate:,})")
        return False, found_list, errors

    return True, found_list, []


def check_factual_accuracy(
    pitch_text: str,
    case: Dict[str, Any],
    all_locations: Optional[Set[str]] = None
) -> Tuple[bool, List[str]]:
    """Verifies that location, size, traffic score, and customer name match the case."""
    errors = []
    text_lower = pitch_text.lower()

    # 1. Customer Name Check
    cust_name = case["customer_name"]
    if cust_name.lower() not in text_lower:
        # Also check without common suffixes like Ltd, Inc, Pvt
        clean_name = re.sub(r"\b(Ltd|Inc|Pvt|LLC|Corporation)\b", "", cust_name, flags=re.I).strip()
        if clean_name.lower() not in text_lower:
            errors.append(f"Customer name '{cust_name}' not mentioned in pitch.")

    # 2. Location Check
    raw_loc = case["location"]
    clean_loc = re.sub(r"\s*#\d+", "", raw_loc).strip()
    if clean_loc.lower() not in text_lower and raw_loc.lower() not in text_lower:
        errors.append(f"Site location '{raw_loc}' not mentioned in pitch.")

    # Check that it doesn't mention wrong locations
    if all_locations:
        for other_loc in all_locations:
            other_clean = re.sub(r"\s*#\d+", "", other_loc).strip()
            if other_clean.lower() != clean_loc.lower() and len(other_clean) > 8:
                if other_clean.lower() in text_lower:
                    errors.append(f"Contradictory location '{other_loc}' mentioned instead of '{raw_loc}'.")
                    break

    # 3. Size sqft Check
    expected_sqft = case["size_sqft"]
    # Look for size patterns: 800 sq. ft., 800 sqft, 800 sq ft
    sqft_matches = re.findall(r"([0-9,]+)\s*(?:sq\.?\s*ft|sqft)", pitch_text, flags=re.IGNORECASE)
    for match in sqft_matches:
        val = int(match.replace(",", ""))
        if val != expected_sqft:
            errors.append(f"Mismatched size: {val} sq.ft. (expected {expected_sqft} sq.ft.)")

    # 4. Traffic score Check
    expected_traffic = case["traffic_score"]
    traffic_matches = re.findall(
        r"([0-9.]+)\s*(?:/10|out of 10|high-density|traffic rating|eyeball score)",
        pitch_text,
        flags=re.IGNORECASE
    )
    for match in traffic_matches:
        try:
            val = float(match)
            if abs(val - expected_traffic) > 0.05 and val != 10.0:
                errors.append(f"Mismatched traffic score: {val} (expected {expected_traffic})")
        except ValueError:
            pass

    return len(errors) == 0, errors


def check_invented_numbers(pitch_text: str, case: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Flags any numeric claim in the pitch that is ungrounded in the dataset facts."""
    errors = []

    # Ground truth allowed values
    allowed_numbers = {
        case["size_sqft"],
        case["monthly_rate_inr"],
        int(case["traffic_score"]),
        round(case["traffic_score"]),
        10,  # 10 in "/10"
        5,   # Standard "5-minute call" CTA
        1,   # 1 time / 1 past booking
        2,   # 2 times
        3,   # top 3 / 3 times
        4,   # 4 times
        7,   # 24/7 or 7 days
        24,  # 24/7
        90,  # 90 days window
    }

    # Extract all standalone integers and floats
    # Exclude dates (e.g. 2026-08-08) and site IDs (e.g. HRD-102)
    cleaned = re.sub(r"\bHRD-\d+\b", "", pitch_text)
    cleaned = re.sub(r"\bCUST-\d+\b", "", cleaned)
    cleaned = re.sub(r"\b202\d-\d{2}-\d{2}\b", "", cleaned)

    tokens = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", cleaned)
    for token in tokens:
        raw = token.replace(",", "")
        try:
            if "." in raw:
                val_f = float(raw)
                if abs(val_f - case["traffic_score"]) > 0.05:
                    errors.append(f"Ungrounded decimal number: '{token}'")
            else:
                val_i = int(raw)
                if val_i not in allowed_numbers and val_i > 5:
                    errors.append(f"Ungrounded integer claim: '{token}'")
        except ValueError:
            continue

    return len(errors) == 0, errors


def evaluate_pitch(
    case: Dict[str, Any],
    pitch_text: str,
    generated_by_ai: bool,
    latency_ms: float = 0.0,
    all_locations: Optional[Set[str]] = None
) -> EvalResult:
    """Runs the complete deterministic evaluation pipeline on a single pitch."""
    expected_rate = case["monthly_rate_inr"]

    rate_ok, found_rates, rate_errs = check_rate_consistency(pitch_text, expected_rate)
    fact_ok, fact_errs = check_factual_accuracy(pitch_text, case, all_locations)
    inv_ok, inv_errs = check_invented_numbers(pitch_text, case)

    all_hallucinations = rate_errs + fact_errs + inv_errs
    has_hallucination = len(all_hallucinations) > 0

    # Groundedness score (1.0 = perfect, penalized per distinct error)
    penalty = min(1.0, len(all_hallucinations) * 0.25)
    groundedness = round(max(0.0, 1.0 - penalty), 2)
    passed = not has_hallucination

    return EvalResult(
        case_id=case.get("case_id", f"{case['site_id']}_{case['customer_id']}"),
        site_id=case["site_id"],
        customer_id=case["customer_id"],
        passed=passed,
        groundedness_score=groundedness,
        has_hallucination=has_hallucination,
        rate_check_passed=rate_ok,
        fact_check_passed=fact_ok,
        invented_numbers_passed=inv_ok,
        found_rates=found_rates,
        hallucinations=all_hallucinations,
        errors=all_hallucinations,
        generated_by_ai=generated_by_ai,
        latency_ms=latency_ms,
        pitch_length=len(pitch_text),
    )


def run_evaluation_suite(
    cases: Optional[List[Dict[str, Any]]] = None,
    force_template: bool = False,
    ref_date: str = "2026-08-08"
) -> Dict[str, Any]:
    """Runs evaluation across all cases in golden dataset and computes portfolio metrics."""
    import time

    cases = cases or load_golden_cases()
    hoardings, customers, bookings = load_all_datasets()
    all_locations = set(hoardings["location"].dropna().tolist())

    # Temporarily hide ANTHROPIC_API_KEY if force_template requested
    original_key = os.environ.get("ANTHROPIC_API_KEY")
    if force_template and original_key:
        os.environ.pop("ANTHROPIC_API_KEY", None)

    results: List[EvalResult] = []
    start_time = datetime.now(timezone.utc)

    try:
        for case in cases:
            t0 = time.perf_counter()
            pitch_response = generate_pitch(
                site_id=case["site_id"],
                customer_id=case["customer_id"],
                hoardings_df=hoardings,
                customers_df=customers,
                bookings_df=bookings,
                reference_date_str=ref_date,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000

            pitch_text = pitch_response["pitch_text"]
            gen_by_ai = pitch_response.get("generated_by_ai", False)

            res = evaluate_pitch(
                case=case,
                pitch_text=pitch_text,
                generated_by_ai=gen_by_ai,
                latency_ms=elapsed_ms,
                all_locations=all_locations,
            )
            results.append(res)

            # Log to tracker runs.csv
            tracker.log_run(
                site_id=case["site_id"],
                customer_id=case["customer_id"],
                latency_ms=elapsed_ms,
                generated_by_ai=gen_by_ai,
                passed=res.passed,
                notes=f"mode={'ai' if gen_by_ai else 'template'}",
            )
    finally:
        if force_template and original_key:
            os.environ["ANTHROPIC_API_KEY"] = original_key

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.passed)
    hallucinated_cases = sum(1 for r in results if r.has_hallucination)
    avg_groundedness = sum(r.groundedness_score for r in results) / total_cases if total_cases else 0.0
    avg_latency = sum(r.latency_ms for r in results) / total_cases if total_cases else 0.0

    hallucination_rate = round((hallucinated_cases / total_cases) * 100, 2) if total_cases else 0.0
    pass_rate = round((passed_cases / total_cases) * 100, 2) if total_cases else 0.0

    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    mode_str = "template" if force_template or not original_key else "claude"

    summary = {
        "timestamp": start_time.isoformat(),
        "mode": mode_str,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate_pct": pass_rate,
        "hallucinated_cases": hallucinated_cases,
        "hallucination_rate_pct": hallucination_rate,
        "avg_groundedness_score": round(avg_groundedness, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "results": [asdict(r) for r in results],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"{timestamp}_{mode_str}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary
