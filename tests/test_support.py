import unittest

from legal_authority_diff.support import (
    evaluate_phrase_contract,
    html_to_text,
    normalize_text,
)


class SupportContractTests(unittest.TestCase):
    def test_html_to_text(self):
        self.assertEqual(
            normalize_text(html_to_text("<p>Same-sex <b>couples</b> may marry.</p>")),
            "same-sex couples may marry.",
        )

    def test_all_required_phrases_supported(self):
        result = evaluate_phrase_contract(
            "The Court discusses same-sex couples and their right to marry.",
            {"required_phrases": ["same-sex couples", "marry"]},
        )
        self.assertEqual(result["support"], "supported")
        self.assertEqual(result["missing_phrases"], [])

    def test_some_required_phrases_partial(self):
        result = evaluate_phrase_contract(
            "The text discusses same-sex couples.",
            {"required_phrases": ["same-sex couples", "marry"]},
        )
        self.assertEqual(result["support"], "partial")

    def test_no_required_phrases_unsupported(self):
        result = evaluate_phrase_contract(
            "This opinion concerns public schools.",
            {"required_phrases": ["same-sex couples", "marry"]},
        )
        self.assertEqual(result["support"], "unsupported")

    def test_empty_contract_is_unknown(self):
        result = evaluate_phrase_contract("anything", {})
        self.assertEqual(result["support"], "unknown")

    def test_source_hash_is_stable_after_whitespace_normalization(self):
        a = evaluate_phrase_contract(
            "Same-sex    couples\nmay marry.",
            {"required_phrases": ["same-sex couples"]},
        )
        b = evaluate_phrase_contract(
            "Same-sex couples may marry.",
            {"required_phrases": ["same-sex couples"]},
        )
        self.assertEqual(a["source_sha256"], b["source_sha256"])


if __name__ == "__main__":
    unittest.main()
