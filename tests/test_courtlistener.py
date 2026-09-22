import io
import json
import unittest

from legal_authority_diff.courtlistener import (
    apply_lookup,
    enrich_records,
    lookup_citation,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def opener_for(payload):
    def opener(request, timeout=20.0):
        return FakeResponse(payload)
    return opener


class LookupTests(unittest.TestCase):
    def test_found_citation(self):
        result = lookup_citation(
            "576 U.S. 644",
            opener=opener_for([
                {
                    "citation": "576 U.S. 644",
                    "normalized_citations": ["576 U.S. 644"],
                    "status": 200,
                    "error_message": "",
                    "clusters": [{"id": 1, "case_name": "Example"}],
                }
            ]),
        )
        self.assertEqual(result["adapter_state"], "FOUND")
        self.assertEqual(result["status"], 200)

    def test_not_found_citation(self):
        result = lookup_citation(
            "1 U.S. 200",
            opener=opener_for([
                {
                    "citation": "1 U.S. 200",
                    "normalized_citations": ["1 U.S. 200"],
                    "status": 404,
                    "error_message": "Citation not found",
                    "clusters": [],
                }
            ]),
        )
        self.assertEqual(result["adapter_state"], "NOT_FOUND")

    def test_empty_result_is_unparsed_not_fabricated(self):
        result = lookup_citation(
            "not a supported citation form",
            opener=opener_for([]),
        )
        self.assertEqual(result["adapter_state"], "UNPARSED")
        self.assertIsNone(result["status"])


class ApplyLookupTests(unittest.TestCase):
    def test_200_sets_exists_true_and_preserves_evidence(self):
        record = {
            "case_id": "A",
            "authority": {"citation": "576 U.S. 644"},
        }
        result = apply_lookup(
            record,
            {
                "citation": "576 U.S. 644",
                "status": 200,
                "normalized_citations": ["576 U.S. 644"],
                "clusters": [{"id": 10, "case_name": "Example Case"}],
                "error_message": "",
                "adapter_state": "FOUND",
            },
        )
        self.assertTrue(result["authority"]["exists"])
        self.assertEqual(
            result["authority"]["verification"]["lookup_status"],
            "FOUND",
        )

    def test_404_sets_exists_false(self):
        record = {
            "case_id": "A",
            "authority": {"citation": "1 U.S. 200", "exists": True},
        }
        result = apply_lookup(
            record,
            {
                "citation": "1 U.S. 200",
                "status": 404,
                "normalized_citations": ["1 U.S. 200"],
                "clusters": [],
                "error_message": "Citation not found",
                "adapter_state": "NOT_FOUND",
            },
        )
        self.assertFalse(result["authority"]["exists"])

    def test_ambiguous_does_not_turn_uncertainty_into_false(self):
        record = {
            "case_id": "A",
            "authority": {"citation": "1 H. 150"},
        }
        result = apply_lookup(
            record,
            {
                "citation": "1 H. 150",
                "status": 300,
                "normalized_citations": ["1 Handy 150", "1 Haw. 150"],
                "clusters": [{"id": 1}, {"id": 2}],
                "error_message": "",
                "adapter_state": "AMBIGUOUS",
            },
        )
        self.assertNotIn("exists", result["authority"])
        self.assertEqual(
            result["authority"]["verification"]["lookup_status"],
            "AMBIGUOUS",
        )

    def test_enrich_records_handles_missing_citation_without_network(self):
        result = enrich_records(
            [{"case_id": "A", "authority": {}}],
            opener=opener_for([]),
            delay_seconds=0,
        )
        self.assertEqual(
            result[0]["authority"]["verification"]["lookup_status"],
            "NO_CITATION",
        )


if __name__ == "__main__":
    unittest.main()
