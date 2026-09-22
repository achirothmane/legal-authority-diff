import unittest

from legal_authority_diff.schema_relation_v011 import (
    safe_treatment,
    treatment_from_stance,
    validate_relation_extraction,
)


CONTEXT = (
    "We therefore refuse to extend Randolph to the very different situation "
    "in this case. Georgia v. Randolph, 547 U.S. 103, concerned a physically "
    "present objecting occupant."
)


def valid_record(**overrides):
    record = {
        "target_authority": {
            "name": "Georgia v. Randolph",
            "citation": "547 U.S. 103",
            "resolved": True,
        },
        "proposition": "Randolph concerned a physically present objecting occupant.",
        "proposition_owner": "CURRENT_COURT",
        "current_court_stance": "DECLINES_TO_EXTEND",
        "treatment": "DISTINGUISHES_OR_LIMITS",
        "claim_consequence": "LIMITS",
        "evidence_spans": [
            {
                "text": "refuse to extend Randolph",
                "role": "STANCE",
            },
            {
                "text": "Georgia v. Randolph, 547 U.S. 103",
                "role": "TARGET_MENTION",
            },
        ],
        "confidence": "high",
        "abstain": False,
        "abstention_reason": None,
    }
    record.update(overrides)
    return record


class V011SchemaTests(unittest.TestCase):
    def test_stance_mapping_is_deterministic(self):
        self.assertEqual(
            treatment_from_stance("DECLINES_TO_EXTEND"),
            "DISTINGUISHES_OR_LIMITS",
        )
        self.assertEqual(
            treatment_from_stance("DECLINES_TO_OVERRULE"),
            "AFFIRMATIVE_USE",
        )
        self.assertEqual(
            treatment_from_stance("OVERRULES"),
            "NEGATIVE_TREATMENT",
        )
        self.assertEqual(
            treatment_from_stance("QUOTES"),
            "MENTION_ONLY",
        )

    def test_valid_grounded_extraction_passes(self):
        result = validate_relation_extraction(
            valid_record(),
            context=CONTEXT,
            expected_target_name="Georgia v. Randolph",
            expected_target_citation="547 U.S. 103",
        )
        self.assertTrue(result["valid"], result["errors"])

    def test_question_about_application_cannot_override_decline_to_extend(self):
        record = valid_record(
            current_court_stance="APPLIES",
            treatment="DISTINGUISHES_OR_LIMITS",
        )
        result = validate_relation_extraction(
            record,
            context=CONTEXT,
            expected_target_name="Georgia v. Randolph",
            expected_target_citation="547 U.S. 103",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("treatment_stance_mismatch" in error for error in result["errors"])
        )

    def test_ungrounded_evidence_is_rejected(self):
        record = valid_record()
        record["evidence_spans"][0]["text"] = "this sentence does not exist"
        result = validate_relation_extraction(
            record,
            context=CONTEXT,
            expected_target_name="Georgia v. Randolph",
            expected_target_citation="547 U.S. 103",
        )
        self.assertFalse(result["valid"])
        self.assertIn("evidence_0_not_grounded", result["errors"])

    def test_target_citation_mismatch_is_rejected(self):
        record = valid_record()
        record["target_authority"]["citation"] = "999 U.S. 999"
        result = validate_relation_extraction(
            record,
            context=CONTEXT,
            expected_target_name="Georgia v. Randolph",
            expected_target_citation="547 U.S. 103",
        )
        self.assertFalse(result["valid"])
        self.assertIn("target_citation_mismatch", result["errors"])

    def test_unresolved_target_requires_abstention(self):
        record = valid_record(
            target_authority={
                "name": "Georgia v. Randolph",
                "citation": "547 U.S. 103",
                "resolved": False,
            },
            current_court_stance="UNRESOLVED",
            treatment="UNKNOWN",
            claim_consequence="UNKNOWN",
            confidence="low",
            abstain=True,
            abstention_reason="target cannot be resolved in the passage",
            evidence_spans=[],
        )
        result = validate_relation_extraction(
            record,
            context=CONTEXT,
            expected_target_name="Georgia v. Randolph",
            expected_target_citation="547 U.S. 103",
        )
        self.assertTrue(result["valid"], result["errors"])

    def test_invalid_extraction_fails_open_to_unknown(self):
        record = valid_record()
        record["evidence_spans"][0]["text"] = "fabricated evidence span"
        result = safe_treatment(
            record,
            context=CONTEXT,
            expected_target_name="Georgia v. Randolph",
            expected_target_citation="547 U.S. 103",
        )
        self.assertFalse(result["usable"])
        self.assertEqual(result["treatment"], "UNKNOWN")

    def test_extra_keys_are_rejected(self):
        record = valid_record()
        record["reasoning"] = "hidden chain of thought must not be part of contract"
        result = validate_relation_extraction(
            record,
            context=CONTEXT,
            expected_target_name="Georgia v. Randolph",
            expected_target_citation="547 U.S. 103",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any(error.startswith("extra_keys:") for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
