import json
import unittest
from pathlib import Path

from legal_authority_diff.engine import diff_runs


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmarks" / "synthetic"


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class SyntheticFalsificationSuiteTests(unittest.TestCase):
    def test_expected_summary_and_case_classifications(self):
        baseline = read_jsonl(SUITE / "baseline.jsonl")
        candidate = read_jsonl(SUITE / "candidate.jsonl")
        expected = json.loads((SUITE / "expected.json").read_text(encoding="utf-8"))

        report = diff_runs(baseline, candidate)

        self.assertEqual(report["summary"], expected["expected_summary"])

        actual_by_case = {
            item["case_id"]: item["classification"]
            for item in report["cases"]
        }
        self.assertEqual(actual_by_case, expected["expected_cases"])

    def test_all_regression_cases_are_blocking(self):
        report = diff_runs(
            read_jsonl(SUITE / "baseline.jsonl"),
            read_jsonl(SUITE / "candidate.jsonl"),
        )

        regressions = [
            item for item in report["cases"]
            if item["classification"] == "REGRESSION"
        ]

        self.assertEqual(len(regressions), 20)
        self.assertTrue(all(item["blocking"] for item in regressions))

    def test_non_regression_review_states_do_not_block(self):
        report = diff_runs(
            read_jsonl(SUITE / "baseline.jsonl"),
            read_jsonl(SUITE / "candidate.jsonl"),
        )

        for item in report["cases"]:
            if item["classification"] in {"UNKNOWN", "WORLD_CHANGE"}:
                self.assertFalse(item["blocking"])


if __name__ == "__main__":
    unittest.main()
