"""Pytest test suite for pitch quality, fact groundedness, and hallucination evaluation.

Tests:
1. Golden dataset structural integrity.
2. Deterministic fact, rate, and ungrounded number checks per golden case.
3. Portfolio-wide quality evaluation for template fallback mode (saving results/<timestamp>.json).
4. Portfolio-wide quality evaluation for Claude LLM mode (cleanly skipped if no API key).
5. DeepEval Faithfulness & Hallucination metrics (cleanly skipped if no API key).
"""

import os
import pytest
from pathlib import Path

from app.data_loader import load_all_datasets
from app.pitch import generate_pitch
from evals.evaluator import (
    evaluate_pitch,
    load_golden_cases,
    run_evaluation_suite,
)

GOLDEN_CASES = load_golden_cases()


def test_golden_dataset_integrity():
    """Verify that the golden dataset has 30 well-formed test cases with required schema."""
    assert len(GOLDEN_CASES) == 30
    for case in GOLDEN_CASES:
        assert "site_id" in case
        assert "customer_id" in case
        assert "location" in case
        assert "size_sqft" in case
        assert "traffic_score" in case
        assert "monthly_rate_inr" in case
        assert "customer_name" in case
        assert "industry" in case
        assert "budget_band" in case
        assert isinstance(case["monthly_rate_inr"], int)
        assert case["monthly_rate_inr"] > 0


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[c["case_id"] for c in GOLDEN_CASES])
def test_pitch_deterministic_groundedness(case):
    """Verifies that each generated pitch passes rate, fact, and number grounding checks."""
    hoardings, customers, bookings = load_all_datasets()
    all_locations = set(hoardings["location"].dropna().tolist())

    resp = generate_pitch(
        site_id=case["site_id"],
        customer_id=case["customer_id"],
        hoardings_df=hoardings,
        customers_df=customers,
        bookings_df=bookings,
        reference_date_str="2026-08-08",
    )

    eval_res = evaluate_pitch(
        case=case,
        pitch_text=resp["pitch_text"],
        generated_by_ai=resp.get("generated_by_ai", False),
        all_locations=all_locations,
    )

    assert eval_res.rate_check_passed, f"Rate check failed: {eval_res.errors}"
    assert eval_res.fact_check_passed, f"Fact check failed: {eval_res.errors}"
    assert eval_res.invented_numbers_passed, f"Invented number check failed: {eval_res.errors}"
    assert eval_res.passed, f"Evaluation failed: {eval_res.errors}"
    assert eval_res.groundedness_score == 1.0


def test_portfolio_evaluation_template_mode():
    """Runs 30 golden cases in template mode, verifies 0% hallucination rate, and saves report."""
    summary = run_evaluation_suite(cases=GOLDEN_CASES, force_template=True)

    print(f"\n[Template Mode] Evaluated {summary['total_cases']} cases:")
    print(f"  Pass Rate: {summary['pass_rate_pct']}%")
    print(f"  Hallucination Rate: {summary['hallucination_rate_pct']}%")
    print(f"  Avg Groundedness: {summary['avg_groundedness_score']}/1.0")
    print(f"  Avg Latency: {summary['avg_latency_ms']} ms")

    assert summary["total_cases"] == 30
    assert summary["hallucination_rate_pct"] == 0.0
    assert summary["pass_rate_pct"] == 100.0
    assert summary["avg_groundedness_score"] == 1.0


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not configured")
def test_portfolio_evaluation_claude_mode():
    """Runs 30 golden cases with Claude API enabled, reporting real metrics to results/."""
    summary = run_evaluation_suite(cases=GOLDEN_CASES, force_template=False)

    print(f"\n[Claude Mode] Evaluated {summary['total_cases']} cases:")
    print(f"  Pass Rate: {summary['pass_rate_pct']}%")
    print(f"  Hallucination Rate: {summary['hallucination_rate_pct']}%")
    print(f"  Avg Groundedness: {summary['avg_groundedness_score']}/1.0")
    print(f"  Avg Latency: {summary['avg_latency_ms']} ms")

    assert summary["total_cases"] == 30
    # Must meet strict accuracy bar
    assert summary["pass_rate_pct"] >= 90.0


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not configured for DeepEval")
def test_deepeval_faithfulness_metric():
    """DeepEval Faithfulness & Hallucination test using Claude as judge model."""
    from deepeval.metrics import FaithfulnessMetric, HallucinationMetric
    from deepeval.test_case import LLMTestCase
    from deepeval.models.base_model import DeepEvalBaseLLM
    import httpx

    class ClaudeJudgeModel(DeepEvalBaseLLM):
        def __init__(self, model_name="claude-3-5-sonnet-20241022"):
            self.model_name = model_name
            self.api_key = os.getenv("ANTHROPIC_API_KEY")

        def load_model(self):
            return self

        def generate(self, prompt: str) -> str:
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30.0,
            )
            return resp.json()["content"][0]["text"]

        async def a_generate(self, prompt: str) -> str:
            return self.generate(prompt)

        def get_model_name(self):
            return self.model_name

    case = GOLDEN_CASES[0]
    hoardings, customers, bookings = load_all_datasets()
    resp = generate_pitch(
        site_id=case["site_id"],
        customer_id=case["customer_id"],
        hoardings_df=hoardings,
        customers_df=customers,
        bookings_df=bookings,
    )

    context = [
        f"Site ID: {case['site_id']}",
        f"Location: {case['location']}",
        f"Size: {case['size_sqft']} sqft",
        f"Traffic Score: {case['traffic_score']}/10",
        f"Monthly Rate: INR {case['monthly_rate_inr']}",
        f"Target Customer: {case['customer_name']}",
    ]

    test_case = LLMTestCase(
        input=f"Write a sales pitch for {case['customer_name']} for billboard at {case['location']}",
        actual_output=resp["pitch_text"],
        retrieval_context=context,
        context=context,
    )

    judge = ClaudeJudgeModel()
    metric = FaithfulnessMetric(threshold=0.8, model=judge)
    metric.measure(test_case)
    assert metric.score >= 0.8
