import unittest

from legal_authority_diff.benchmark import (
    evaluate_binary,
    score_claim_against_source,
)


class LexicalSupportScoreTests(unittest.TestCase):
    def test_related_sentence_scores_above_unrelated_sentence(self):
        claim = "Police must advise a person in custody about silence and counsel before interrogation."
        related = (
            "Before questioning, a person in custody must be warned that he has a right "
            "to remain silent and a right to the presence of an attorney."
        )
        unrelated = (
            "State laws barring interracial marriage were challenged under the Fourteenth Amendment."
        )

        related_score = score_claim_against_source(claim, related)["score"]
        unrelated_score = score_claim_against_source(claim, unrelated)["score"]

        self.assertGreater(related_score, unrelated_score)

    def test_short_two_sentence_window_can_capture_support(self):
        claim = "Student speech is protected unless school officials forecast substantial disruption."
        text = (
            "Students retain constitutional freedoms in school. "
            "Officials may act when they reasonably forecast substantial disruption of school discipline."
        )
        result = score_claim_against_source(claim, text)
        self.assertGreater(result["score"], 0.30)

    def test_metrics_count_false_positives_and_negatives(self):
        report = evaluate_binary(
            [
                {"score": 0.8, "expected_support": "supported"},
                {"score": 0.1, "expected_support": "supported"},
                {"score": 0.7, "expected_support": "unsupported"},
                {"score": 0.2, "expected_support": "unsupported"},
            ],
            threshold=0.5,
        )
        self.assertEqual(report["counts"]["tp"], 1)
        self.assertEqual(report["counts"]["tn"], 1)
        self.assertEqual(report["counts"]["fp"], 1)
        self.assertEqual(report["counts"]["fn"], 1)
        self.assertEqual(report["metrics"]["accuracy"], 0.5)


if __name__ == "__main__":
    unittest.main()
