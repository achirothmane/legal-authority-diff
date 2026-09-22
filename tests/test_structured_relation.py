import unittest

from legal_authority_diff.structured_relation_v010 import extract_structured_relation


class StructuredRelationTests(unittest.TestCase):
    def test_target_holding_content_is_not_current_limitation(self):
        result = extract_structured_relation(
            'Specifically, in Hildwin, this Court held that the Sixth Amendment '
            '"does not require that the specific findings authorizing the '
            'imposition of the sentence of death be made by the jury."',
            target_citation="490 U.S. 638",
            target_term="Hildwin",
        )
        self.assertEqual(result["attribution_owner"], "TARGET_AUTHORITY")
        self.assertEqual(result["relation"], "MENTION_ONLY")
        self.assertIn("does not require", result["attributed_proposition"])

    def test_current_court_overrule_is_negative_treatment(self):
        result = extract_structured_relation(
            "Bowers v. Hardwick, 478 U.S. 186, should be and now is overruled.",
            target_citation="478 U.S. 186",
            target_term="Bowers v. Hardwick",
        )
        self.assertEqual(result["relation"], "NEGATIVE_TREATMENT")
        self.assertIn("OVERRULE", result["current_court_actions"])

    def test_current_court_under_target_is_affirmative(self):
        result = extract_structured_relation(
            "Under Terry v. Ohio, 392 U.S. 1, the officer needed reasonable suspicion.",
            target_citation="392 U.S. 1",
            target_term="Terry",
        )
        self.assertEqual(result["relation"], "AFFIRMATIVE_USE")
        self.assertIn("APPLY", result["current_court_actions"])

    def test_current_court_declines_to_extend_target(self):
        result = extract_structured_relation(
            "We therefore decline to extend Robinson, 414 U.S. 218, to searches "
            "of data on cell phones.",
            target_citation="414 U.S. 218",
            target_term="Robinson",
        )
        self.assertEqual(result["relation"], "DISTINGUISHES_OR_LIMITS")

    def test_other_case_overrule_does_not_contaminate_target(self):
        result = extract_structured_relation(
            "We overrule Smith v. Jones, 400 U.S. 10. "
            "Miranda v. Arizona, 384 U.S. 436, is discussed elsewhere.",
            target_citation="384 U.S. 436",
            target_term="Miranda",
        )
        self.assertEqual(result["relation"], "MENTION_ONLY")

    def test_target_absent_is_unknown(self):
        result = extract_structured_relation(
            "The Court applies Miranda to the interrogation.",
            target_citation="372 U.S. 335",
            target_term="Gideon",
        )
        self.assertEqual(result["relation"], "UNKNOWN")
        self.assertFalse(result["target_present"])


if __name__ == "__main__":
    unittest.main()
