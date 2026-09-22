import unittest

from legal_authority_diff.relation_policy_v011 import classify_v011_transition


CONTEXT = (
    "We therefore refuse to extend Randolph to the very different situation "
    "in this case. Georgia v. Randolph, 547 U.S. 103, concerned a physically "
    "present objecting occupant."
)


def extraction(stance, treatment, *, abstain=False, confidence="high"):
    if abstain:
        evidence = []
        reason = "cannot resolve treatment"
    else:
        evidence = [
            {"text": "Georgia v. Randolph, 547 U.S. 103", "role": "TARGET_MENTION"},
            {
                "text": (
                    "refuse to extend Randolph"
                    if stance == "DECLINES_TO_EXTEND"
                    else "Georgia v. Randolph, 547 U.S. 103"
                ),
                "role": "STANCE",
            },
        ]
        reason = None

    return {
        "target_authority": {
            "name": "Georgia v. Randolph",
            "citation": "547 U.S. 103",
            "resolved": not abstain,
        },
        "proposition": "",
        "proposition_owner": "CURRENT_COURT" if not abstain else "UNKNOWN",
        "current_court_stance": stance,
        "treatment": treatment,
        "claim_consequence": "LIMITS" if treatment == "DISTINGUISHES_OR_LIMITS" else "UNKNOWN",
        "evidence_spans": evidence,
        "confidence": confidence,
        "abstain": abstain,
        "abstention_reason": reason,
    }


class V011PolicyBridgeTests(unittest.TestCase):
    def test_limiting_relation_becomes_unknown_not_block(self):
        result = classify_v011_transition(
            baseline_score=0.8,
            candidate_score=0.8,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            extraction=extraction(
                "DECLINES_TO_EXTEND",
                "DISTINGUISHES_OR_LIMITS",
            ),
            context=CONTEXT,
            target_name="Georgia v. Randolph",
            target_citation="547 U.S. 103",
        )
        self.assertEqual(result["classification"], "UNKNOWN")

    def test_valid_abstention_stays_unknown_even_if_role_would_regress(self):
        result = classify_v011_transition(
            baseline_score=0.8,
            candidate_score=0.8,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            extraction=extraction(
                "UNRESOLVED",
                "UNKNOWN",
                abstain=True,
                confidence="low",
            ),
            context=CONTEXT,
            target_name="Georgia v. Randolph",
            target_citation="547 U.S. 103",
        )
        self.assertEqual(result["classification"], "UNKNOWN")
        self.assertEqual(result["reason"], "v0.11:validated_abstention")

    def test_invalid_semantics_cannot_reach_blocking_policy(self):
        bad = extraction("APPLIES", "DISTINGUISHES_OR_LIMITS")
        result = classify_v011_transition(
            baseline_score=0.8,
            candidate_score=0.1,
            baseline_role="COURT_SELF_HOLDING",
            candidate_role="ATTRIBUTED_PRIOR_AUTHORITY",
            extraction=bad,
            context=CONTEXT,
            target_name="Georgia v. Randolph",
            target_citation="547 U.S. 103",
        )
        self.assertEqual(result["classification"], "UNKNOWN")
        self.assertEqual(result["candidate_relation"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
