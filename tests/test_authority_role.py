import unittest

from legal_authority_diff.authority_role import (
    classify_authority_role,
    compare_authority_roles,
)


class AuthorityRoleTests(unittest.TestCase):
    def test_reporter_syllabus_holding(self):
        result = classify_authority_role(
            "Held: The right of an indigent defendant to counsel is fundamental."
        )
        self.assertEqual(result["role"], "REPORTER_SYLLABUS_HOLDING")

    def test_court_self_holding_wins_even_with_prior_citation(self):
        result = classify_authority_role(
            "We therefore hold that the search was unreasonable. See 365 U. S. 505."
        )
        self.assertEqual(result["role"], "COURT_SELF_HOLDING")

    def test_we_think_that_rule_is_self_holding_cue(self):
        result = classify_authority_role(
            "We think that obtaining information about the home by sense-enhancing "
            "technology constitutes a search—Silverman, 365 U. S. 505."
        )
        self.assertEqual(result["role"], "COURT_SELF_HOLDING")

    def test_law_review_is_secondary_source(self):
        result = classify_authority_role(
            "Birzon, The Right to Counsel and the Indigent Accused, 14 Buffalo L. Rev. 1."
        )
        self.assertEqual(result["role"], "SECONDARY_SOURCE")

    def test_attributed_prior_case(self):
        result = classify_authority_role(
            "As we held in Gideon v. Wainwright, 372 U.S. 335, counsel is fundamental."
        )
        self.assertEqual(result["role"], "ATTRIBUTED_PRIOR_AUTHORITY")

    def test_unknown_does_not_guess(self):
        result = classify_authority_role(
            "The parties dispute whether the record satisfies the applicable standard."
        )
        self.assertEqual(result["role"], "UNKNOWN")

    def test_primary_to_secondary_is_regression(self):
        result = compare_authority_roles(
            "COURT_SELF_HOLDING",
            "SECONDARY_SOURCE",
        )
        self.assertEqual(result["classification"], "REGRESSION")

    def test_primary_to_attributed_is_regression(self):
        result = compare_authority_roles(
            "REPORTER_SYLLABUS_HOLDING",
            "ATTRIBUTED_PRIOR_AUTHORITY",
        )
        self.assertEqual(result["classification"], "REGRESSION")

    def test_primary_to_unknown_is_not_forced_regression(self):
        result = compare_authority_roles(
            "COURT_SELF_HOLDING",
            "UNKNOWN",
        )
        self.assertEqual(result["classification"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
