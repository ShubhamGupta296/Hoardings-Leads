"""Quality tracking for sales pitch generation runs.

Logs request metadata, latency, token usage, cost estimates, and pass/fail metrics
to backend/evals/results/runs.csv for longitudinal quality and cost monitoring.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RUNS_FILE = RESULTS_DIR / "runs.csv"

# Cost per 1M tokens for Claude 3.5 Sonnet ($3 input, $15 output)
SONNET_INPUT_PER_M = 3.00
SONNET_OUTPUT_PER_M = 15.00

CSV_HEADERS = [
    "timestamp",
    "site_id",
    "customer_id",
    "latency_ms",
    "generated_by_ai",
    "passed",
    "input_tokens",
    "output_tokens",
    "estimated_cost_usd",
    "notes",
]


def estimate_claude_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculates estimated cost in USD for Claude 3.5 Sonnet."""
    cost = (input_tokens / 1_000_000 * SONNET_INPUT_PER_M) + (
        output_tokens / 1_000_000 * SONNET_OUTPUT_PER_M
    )
    return round(cost, 6)


class PitchTracker:
    def __init__(self, log_path: Path = RUNS_FILE):
        self.log_path = log_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)

    def log_run(
        self,
        site_id: str,
        customer_id: str,
        latency_ms: float,
        generated_by_ai: bool,
        passed: bool,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: Optional[float] = None,
        notes: str = "",
    ) -> dict:
        """Appends a new pitch execution run to runs.csv."""
        if estimated_cost_usd is None and generated_by_ai:
            estimated_cost_usd = estimate_claude_cost(input_tokens, output_tokens)
        elif estimated_cost_usd is None:
            estimated_cost_usd = 0.0

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "site_id": site_id,
            "customer_id": customer_id,
            "latency_ms": round(latency_ms, 2),
            "generated_by_ai": generated_by_ai,
            "passed": passed,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "notes": notes,
        }

        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writerow(record)

        return record


# Global default tracker
tracker = PitchTracker()
