import unittest

from legal_authority_diff.relation_policy_v09 import (
    classify_relation_aware_transition,
)


class RelationAwarePolicyTests(unittest.TestCase):
    def test_affirmative_use_prevents_role_only_false_block(self):
        result = classify_relation_aware_transition(
            baseline_score=0.50,
            candidate_score=0.45,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            candidate_relation="AFFIRMATIVE_USE",
        )
        self.assertEqual(
            result["classification"],
            "NO_REGRESSION_DETECTED",
        )
        self.assertEqual(result["reason"], "affirmative_precedent_use")

    def test_affirmative_use_does_not_rescue_failed_support(self):
        result = classify_relation_aware_transition(
            baseline_score=0.50,
            candidate_score=0.20,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            candidate_relation="AFFIRMATIVE_USE",
        )
        self.assertEqual(result["classification"], "REGRESSION")
        self.assertEqual(result["reason"], "lexical_support")

    def test_negative_treatment_becomes_world_change(self):
        result = classify_relation_aware_transition(
            baseline_score=0.50,
            candidate_score=0.50,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="COURT_SELF_HOLDING",
            candidate_relation="NEGATIVE_TREATMENT",
        )
        self.assertEqual(result["classification"], "WORLD_CHANGE")

    def test_distinguishing_relation_abstains(self):
        result = classify_relation_aware_transition(
            baseline_score=0.50,
            candidate_score=0.45,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            candidate_relation="DISTINGUISHES_OR_LIMITS",
        )
        self.assertEqual(result["classification"], "UNKNOWN")

    def test_mixed_relation_abstains(self):
        result = classify_relation_aware_transition(
            baseline_score=0.50,
            candidate_score=0.45,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            candidate_relation="MIXED_OR_CONFLICTING",
        )
        self.assertEqual(result["classification"], "UNKNOWN")
        self.assertEqual(result["reason"], "mixed_or_conflicting_relation")

    def test_mention_only_falls_back_to_v07_role_regression(self):
        result = classify_relation_aware_transition(
            baseline_score=0.50,
            candidate_score=0.45,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            candidate_relation="MENTION_ONLY",
        )
        self.assertEqual(result["classification"], "REGRESSION")
        self.assertTrue(result["reason"].startswith("v0.7_fallback:"))


if __name__ == "__main__":
    unittest.main()
