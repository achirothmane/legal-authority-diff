import unittest

from legal_authority_diff.semantic import (
    lexical_retrieval_score,
    normalize_nli_output,
    rank_candidate_windows,
    source_windows,
)


class SemanticRetrievalTests(unittest.TestCase):
    def test_source_windows_include_one_and_two_sentence_chunks(self):
        windows = source_windows("Alpha one. Beta two. Gamma three.")
        self.assertIn("Alpha one.", windows)
        self.assertIn("Alpha one. Beta two.", windows)
        self.assertIn("Beta two. Gamma three.", windows)

    def test_related_window_ranks_above_unrelated_window(self):
        claim = "Police need reasonable suspicion for a brief investigatory stop."
        source = (
            "The case discusses tax accounting. "
            "An officer may conduct a brief investigatory stop when specific facts "
            "create reasonable suspicion of criminal activity. "
            "The judgment was affirmed."
        )
        ranked = rank_candidate_windows(claim, source, top_k=2)
        self.assertIn("reasonable suspicion", ranked[0]["window"].lower())

    def test_lexical_retrieval_is_topic_signal_not_final_support(self):
        claim = "A defendant has a right to appointed counsel."
        topical = "The suspect asked to speak with counsel during interrogation."
        unrelated = "The dispute concerns minimum contacts with the forum state."
        self.assertGreater(
            lexical_retrieval_score(claim, topical),
            lexical_retrieval_score(claim, unrelated),
        )


class NliOutputTests(unittest.TestCase):
    def test_label_mapping_uses_model_config_not_hardcoded_order(self):
        result = normalize_nli_output(
            [0.0, 2.0, -1.0],
            {
                0: "neutral",
                1: "entailment",
                2: "contradiction",
            },
        )
        self.assertGreater(result["entailment"], result["neutral"])
        self.assertGreater(result["entailment"], result["contradiction"])

    def test_softmax_probabilities_sum_to_one(self):
        result = normalize_nli_output(
            [1.0, 2.0, 3.0],
            {
                0: "contradiction",
                1: "entailment",
                2: "neutral",
            },
        )
        self.assertAlmostEqual(sum(result.values()), 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
