import unittest

from legal_authority_diff.authority_relation_v09 import (
    classify_precedent_relation,
    extract_anchor_context,
)


class AuthorityRelationTests(unittest.TestCase):
    def test_reaffirmation_is_affirmative_use(self):
        result = classify_precedent_relation(
            "This Court declines to overrule Miranda, 384 U.S. 436. "
            "The rule remains in force.",
            target_citation="384 U.S. 436",
            target_term="Miranda",
        )
        self.assertEqual(result["relation"], "AFFIRMATIVE_USE")

    def test_application_is_affirmative_use(self):
        result = classify_precedent_relation(
            "Strickland v. Washington, 466 U.S. 668, applies to the claim.",
            target_citation="466 U.S. 668",
            target_term="Strickland",
        )
        self.assertEqual(result["relation"], "AFFIRMATIVE_USE")

    def test_under_target_is_affirmative_use(self):
        result = classify_precedent_relation(
            "Under Terry v. Ohio, 392 U.S. 1, the officer needed reasonable suspicion.",
            target_citation="392 U.S. 1",
            target_term="Terry",
        )
        self.assertEqual(result["relation"], "AFFIRMATIVE_USE")

    def test_distinguishing_is_not_application(self):
        result = classify_precedent_relation(
            "In contrast to Crawford, 541 U.S. 36, the statements were made "
            "during an ongoing emergency.",
            target_citation="541 U.S. 36",
            target_term="Crawford",
        )
        self.assertEqual(result["relation"], "DISTINGUISHES_OR_LIMITS")

    def test_overruling_is_negative_treatment(self):
        result = classify_precedent_relation(
            "Michigan v. Jackson, 475 U.S. 625, should be and now is overruled.",
            target_citation="475 U.S. 625",
            target_term="Michigan v. Jackson",
        )
        self.assertEqual(result["relation"], "NEGATIVE_TREATMENT")

    def test_short_of_overrule_negative_treatment(self):
        result = classify_precedent_relation(
            "Example v. State, 400 U.S. 10, is no longer controlling on this point.",
            target_citation="400 U.S. 10",
            target_term="Example v. State",
        )
        self.assertEqual(result["relation"], "NEGATIVE_TREATMENT")

    def test_procedure_no_longer_mandatory_is_negative_treatment(self):
        result = classify_precedent_relation(
            "Saucier v. Katz, 533 U.S. 194, should no longer be regarded as "
            "mandatory in all cases.",
            target_citation="533 U.S. 194",
            target_term="Saucier",
        )
        self.assertEqual(result["relation"], "NEGATIVE_TREATMENT")

    def test_plain_historical_reference_is_mention_only(self):
        result = classify_precedent_relation(
            "In the wake of Miranda v. Arizona, 384 U.S. 436, Congress enacted "
            "a statute concerning admissibility.",
            target_citation="384 U.S. 436",
            target_term="Miranda",
        )
        self.assertEqual(result["relation"], "MENTION_ONLY")

    def test_relation_word_about_other_case_does_not_contaminate_target(self):
        result = classify_precedent_relation(
            "We overrule Smith v. Jones, 400 U.S. 10. "
            "Miranda v. Arizona, 384 U.S. 436, is also discussed in the briefs.",
            target_citation="384 U.S. 436",
            target_term="Miranda",
        )
        self.assertEqual(result["relation"], "MENTION_ONLY")

    def test_affirmative_word_about_other_case_does_not_contaminate_target(self):
        result = classify_precedent_relation(
            "We reaffirm Smith v. Jones, 400 U.S. 10. "
            "Crawford v. Washington, 541 U.S. 36, is distinguishable here.",
            target_citation="541 U.S. 36",
            target_term="Crawford",
        )
        self.assertEqual(result["relation"], "DISTINGUISHES_OR_LIMITS")

    def test_mixed_target_linked_cues_abstain_as_mixed(self):
        result = classify_precedent_relation(
            "Under Terry v. Ohio, 392 U.S. 1, reasonable suspicion is required. "
            "Unlike Terry, however, the encounter here involved no seizure.",
            target_citation="392 U.S. 1",
            target_term="Terry",
        )
        self.assertEqual(result["relation"], "MIXED_OR_CONFLICTING")
        self.assertEqual(
            set(result["categories"]),
            {"AFFIRMATIVE_USE", "DISTINGUISHES_OR_LIMITS"},
        )

    def test_absent_target_is_unknown(self):
        result = classify_precedent_relation(
            "The Daubert factors may apply to engineering testimony.",
            target_citation="372 U.S. 335",
            target_term="Gideon",
        )
        self.assertEqual(result["relation"], "UNKNOWN")

    def test_anchor_context_collapses_pdf_whitespace(self):
        context = extract_anchor_context(
            "Alpha\n\nThis Court   declines to overrule Miranda. Omega",
            "This Court declines to overrule Miranda",
            radius=10,
        )
        self.assertIn("declines to overrule Miranda", context)

    def test_anchor_context_tolerates_minor_wording_drift(self):
        context = extract_anchor_context(
            "Before. The Roberts test departs from historical principles because "
            "the framework admits statements on a reliability finding. After.",
            "The Roberts test departs from the historical principles identified above",
            radius=10,
        )
        self.assertIn("Roberts test departs from historical principles", context)

    def test_anchor_context_does_not_force_unrelated_approximate_match(self):
        context = extract_anchor_context(
            "The weather report discusses coastal winds and rainfall.",
            "The Roberts test departs from the historical principles identified above",
            radius=10,
        )
        self.assertEqual(context, "")

    def test_anchor_context_tolerates_ocr_split_inside_name(self):
        context = extract_anchor_context(
            "Held: Miller-El is entitled to prevail on his Ba tson claim and obtain relief.",
            "entitled to prevail on his Batson claim",
            radius=10,
        )
        self.assertIn("Ba tson claim", context)


if __name__ == "__main__":
    unittest.main()
