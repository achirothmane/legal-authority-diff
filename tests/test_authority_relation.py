import unittest

from legal_authority_diff.authority_relation import (
    classify_precedent_relation,
    extract_anchor_context,
)


class AuthorityRelationTests(unittest.TestCase):
    def test_reaffirmation_is_affirmative_use(self):
        result = classify_precedent_relation(
            "This Court declines to overrule Miranda. "
            "Miranda, 384 U.S. 436, remains the governing rule.",
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
            target_term="Jackson",
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

    def test_absent_target_is_unknown(self):
        result = classify_precedent_relation(
            "The Daubert factors may apply to engineering testimony.",
            target_citation="372 U.S. 335",
            target_term="Gideon",
        )
        self.assertEqual(result["relation"], "UNKNOWN")

    def test_anchor_context_collapses_pdf_whitespace(self):
        context = extract_anchor_context(
            "Alpha\\n\\nThis Court   declines to overrule Miranda. Omega",
            "This Court declines to overrule Miranda",
            radius=10,
        )
        self.assertIn("declines to overrule Miranda", context)


if __name__ == "__main__":
    unittest.main()
