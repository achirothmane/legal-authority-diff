import unittest

from legal_authority_diff.engine import classify_pair, diff_runs


def case(
    case_id="LAD-001",
    *,
    citation="123 Cal. 4th 456",
    jurisdiction="CA",
    status="controlling",
    treatment="good_law",
    exists=True,
    support="supported",
    world_change=False,
):
    return {
        "case_id": case_id,
        "claim": "California law requires ...",
        "authority": {
            "citation": citation,
            "jurisdiction": jurisdiction,
            "status": status,
            "treatment": treatment,
            "exists": exists,
        },
        "support": support,
        "world_change": world_change,
    }


class ClassifyPairTests(unittest.TestCase):
    def test_authority_downgrade_blocks(self):
        baseline = case()
        candidate = case(
            citation="999 F.3d 123",
            jurisdiction="9th Cir.",
            status="persuasive",
            support="partial",
        )
        result = classify_pair(baseline, candidate)
        self.assertEqual(result["classification"], "REGRESSION")
        self.assertTrue(result["blocking"])
        kinds = {change["kind"] for change in result["changes"]}
        self.assertIn("authority_strength", kinds)
        self.assertIn("proposition_support", kinds)

    def test_fabricated_citation_blocks(self):
        result = classify_pair(case(), case(exists=False))
        self.assertEqual(result["classification"], "REGRESSION")
        self.assertTrue(result["blocking"])

    def test_new_negative_treatment_blocks(self):
        result = classify_pair(case(), case(treatment="overruled"))
        self.assertEqual(result["classification"], "REGRESSION")

    def test_support_downgrade_blocks(self):
        result = classify_pair(case(), case(support="unsupported"))
        self.assertEqual(result["classification"], "REGRESSION")

    def test_world_change_does_not_blame_candidate(self):
        candidate = case(world_change=True)
        candidate["world_change_reason"] = "Statute amended after the baseline snapshot."
        result = classify_pair(case(), candidate)
        self.assertEqual(result["classification"], "WORLD_CHANGE")
        self.assertFalse(result["blocking"])

    def test_equivalent_citation_swap_is_not_a_regression(self):
        result = classify_pair(case(), case(citation="456 Cal. 5th 789"))
        self.assertEqual(result["classification"], "UNCHANGED")

    def test_unranked_jurisdiction_change_requires_review(self):
        result = classify_pair(
            case(status="persuasive", jurisdiction="CA"),
            case(status="persuasive", jurisdiction="NV"),
        )
        self.assertEqual(result["classification"], "UNKNOWN")


class DiffRunsTests(unittest.TestCase):
    def test_any_regression_blocks_run(self):
        baseline = [case("A"), case("B")]
        candidate = [case("A"), case("B", support="unsupported")]
        report = diff_runs(baseline, candidate)
        self.assertEqual(report["summary"]["decision"], "BLOCK")
        self.assertEqual(report["summary"]["regressions"], 1)

    def test_unknown_without_regression_requires_review(self):
        report = diff_runs([case("A")], [])
        self.assertEqual(report["summary"]["decision"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
