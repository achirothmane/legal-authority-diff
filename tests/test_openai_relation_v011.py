import json
import unittest

from legal_authority_diff.openai_relation_v011 import extract_relation_openai


CONTEXT = (
    "We therefore refuse to extend Randolph to the very different situation "
    "in this case. Georgia v. Randolph, 547 U.S. 103, concerned a physically "
    "present objecting occupant."
)


class FakeResponse:
    status = "completed"
    output = []

    def __init__(self, payload):
        self.output_text = json.dumps(payload)


class FakeResponses:
    def __init__(self, payload):
        self.payload = payload
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeResponse(self.payload)


class FakeClient:
    def __init__(self, payload):
        self.responses = FakeResponses(payload)


class V011OpenAIAdapterTests(unittest.TestCase):
    def test_adapter_uses_strict_json_schema_and_validates_output(self):
        payload = {
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
        client = FakeClient(payload)

        result = extract_relation_openai(
            context=CONTEXT,
            target_name="Georgia v. Randolph",
            target_citation="547 U.S. 103",
            model="test-model",
            client=client,
        )

        self.assertTrue(result["validation"]["valid"])
        self.assertTrue(result["policy_input"]["usable"])
        self.assertEqual(
            result["policy_input"]["treatment"],
            "DISTINGUISHES_OR_LIMITS",
        )

        request = client.responses.kwargs
        self.assertFalse(request["store"])
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertNotIn("reasoning_steps", request["text"]["format"]["schema"]["properties"])

    def test_invalid_model_semantics_fail_open(self):
        payload = {
            "target_authority": {
                "name": "Georgia v. Randolph",
                "citation": "547 U.S. 103",
                "resolved": True,
            },
            "proposition": "",
            "proposition_owner": "UNKNOWN",
            "current_court_stance": "APPLIES",
            "treatment": "DISTINGUISHES_OR_LIMITS",
            "claim_consequence": "UNKNOWN",
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
        result = extract_relation_openai(
            context=CONTEXT,
            target_name="Georgia v. Randolph",
            target_citation="547 U.S. 103",
            model="test-model",
            client=FakeClient(payload),
        )
        self.assertFalse(result["validation"]["valid"])
        self.assertFalse(result["policy_input"]["usable"])
        self.assertEqual(result["policy_input"]["treatment"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
