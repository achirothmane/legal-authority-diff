import unittest

from legal_authority_diff.role_diff import classify_evidence_transition


class RoleAwareDiffTests(unittest.TestCase):
    def test_lexical_drop_is_regression(self):
        result = classify_evidence_transition(
            baseline_score=0.50,
            candidate_score=0.20,
            baseline_role="UNKNOWN",
            candidate_role="UNKNOWN",
        )
        self.assertEqual(result["classification"], "REGRESSION")
        self.assertEqual(result["reason"], "lexical_support")

    def test_role_downgrade_recovers_high_scoring_false_positive(self):
        result = classify_evidence_transition(
            baseline_score=0.48,
            candidate_score=0.365,
            baseline_role="REPORTER_SYLLABUS_HOLDING",
            candidate_role="SECONDARY_SOURCE",
        )
        self.assertEqual(result["classification"], "REGRESSION")
        self.assertEqual(result["reason"], "authority_role")

    def test_unknown_role_does_not_create_regression(self):
        result = classify_evidence_transition(
            baseline_score=0.60,
            candidate_score=0.40,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="UNKNOWN",
        )
        self.assertEqual(
            result["classification"],
            "NO_REGRESSION_DETECTED",
        )

    def test_bad_baseline_does_not_create_fake_improvement_or_regression(self):
        result = classify_evidence_transition(
            baseline_score=0.20,
            candidate_score=0.60,
            baseline_role="SECONDARY_SOURCE",
            candidate_role="COURT_SELF_HOLDING",
        )
        self.assertEqual(result["classification"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
