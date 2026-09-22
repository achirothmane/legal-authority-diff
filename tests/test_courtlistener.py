import json
import unittest

from legal_authority_diff.courtlistener import (
    apply_lookup,
    enrich_records,
    infer_federal_authority_status,
    lookup_citation,
    resolve_authority_metadata,
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


def opener_sequence(*payloads):
    queue = list(payloads)

    def opener(request, timeout=20.0):
        if not queue:
            raise AssertionError("Unexpected extra HTTP request")
        return FakeResponse(queue.pop(0))

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


class AuthorityMetadataTests(unittest.TestCase):
    def test_resolves_source_court_from_linked_docket(self):
        lookup = {
            "status": 200,
            "clusters": [
                {
                    "docket": "https://example.test/dockets/1/",
                    "precedential_status": "Published",
                }
            ],
        }
        result = resolve_authority_metadata(
            lookup,
            token="secret",
            opener=opener_for(
                {
                    "id": 1,
                    "docket_number": "14-556",
                    "court": "https://example.test/courts/scotus/",
                    "court_id": "scotus",
                }
            ),
        )
        self.assertEqual(result["authority_metadata_state"], "RESOLVED")
        self.assertEqual(result["source_court_id"], "scotus")
        self.assertEqual(result["precedential_status"], "Published")

    def test_ambiguous_lookup_does_not_guess_source_court(self):
        result = resolve_authority_metadata(
            {"status": 300, "clusters": [{"docket": "x"}, {"docket": "y"}]},
            token="secret",
            opener=opener_for({}),
        )
        self.assertEqual(result["authority_metadata_state"], "UNRESOLVED")
        self.assertNotIn("source_court_id", result)

    def test_scotus_is_controlling_for_federal_circuit_target(self):
        self.assertEqual(
            infer_federal_authority_status("scotus", "ca2", "Published"),
            "controlling",
        )

    def test_same_published_circuit_is_controlling(self):
        self.assertEqual(
            infer_federal_authority_status("ca9", "ca9", "Published"),
            "controlling",
        )

    def test_other_published_circuit_is_persuasive(self):
        self.assertEqual(
            infer_federal_authority_status("ca9", "ca2", "Published"),
            "persuasive",
        )

    def test_unsupported_target_returns_unknown(self):
        self.assertIsNone(
            infer_federal_authority_status("ca9", "nysd", "Published")
        )

    def test_unpublished_circuit_is_not_ranked_in_v03(self):
        self.assertIsNone(
            infer_federal_authority_status("ca9", "ca2", "Unpublished")
        )


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

    def test_real_court_metadata_can_derive_controlling_status(self):
        record = {
            "case_id": "A",
            "context": {"target_court_id": "ca2"},
            "authority": {"citation": "576 U.S. 644"},
        }
        result = apply_lookup(
            record,
            {
                "citation": "576 U.S. 644",
                "status": 200,
                "normalized_citations": ["576 U.S. 644"],
                "clusters": [{"id": 10, "case_name": "Obergefell v. Hodges"}],
                "error_message": "",
                "adapter_state": "FOUND",
                "authority_metadata_state": "RESOLVED",
                "source_court_id": "scotus",
                "source_court_url": "https://example.test/courts/scotus/",
                "docket_id": 1,
                "docket_number": "14-556",
                "precedential_status": "Published",
            },
        )
        self.assertEqual(result["authority"]["status"], "controlling")
        verification = result["authority"]["verification"]
        self.assertEqual(verification["source_court_id"], "scotus")
        self.assertEqual(
            verification["authority_rule"],
            "us-federal-appellate-v0.3",
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

    def test_enrich_records_resolves_court_and_derives_status(self):
        record = {
            "case_id": "A",
            "context": {"target_court_id": "ca2"},
            "authority": {"citation": "771 F.3d 456"},
        }
        opener = opener_sequence(
            [
                {
                    "citation": "771 F.3d 456",
                    "normalized_citations": ["771 F.3d 456"],
                    "status": 200,
                    "error_message": "",
                    "clusters": [
                        {
                            "id": 8442024,
                            "case_name": "Latta v. Otter",
                            "docket": "https://example.test/dockets/2/",
                            "precedential_status": "Published",
                        }
                    ],
                }
            ],
            {
                "id": 2,
                "docket_number": "14-35420",
                "court": "https://example.test/courts/ca9/",
                "court_id": "ca9",
            },
        )
        result = enrich_records(
            [record],
            token="secret",
            opener=opener,
            delay_seconds=0,
        )
        self.assertEqual(result[0]["authority"]["status"], "persuasive")
        self.assertTrue(result[0]["authority"]["exists"])


if __name__ == "__main__":
    unittest.main()
