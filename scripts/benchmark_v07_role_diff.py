import json
from pathlib import Path

from legal_authority_diff.authority_role import classify_window_in_source
from legal_authority_diff.benchmark import _read_jsonl, score_claim_against_source
from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.role_diff import classify_evidence_transition


LEXICAL_THRESHOLD = 0.34


def build_cache(rows):
    cache = {}
    for row in rows:
        citation = str(row["citation"]).strip()
        if citation not in cache:
            cache[citation] = fetch_us_reports_text(citation)
    return cache


def evidence(row, cache):
    source_text, metadata = cache[row["citation"]]
    lexical = score_claim_against_source(row["claim"], source_text)
    role = classify_window_in_source(
        source_text,
        lexical["window_full"],
        context_chars=320,
    )
    return {
        "pair_id": row["pair_id"],
        "claim_id": row["claim_id"],
        "citation": row["citation"],
        "case_name": row["case_name"],
        "score": lexical["score"],
        "display_window": lexical["window"],
        "role": role["role"],
        "role_confidence": role["confidence"],
        "role_cues": role["cues"],
        "source": metadata,
    }


def run_dataset(path):
    rows = _read_jsonl(path)
    positives = {
        row["claim_id"]: row
        for row in rows
        if row["expected_support"] == "supported"
    }
    negatives = {
        row["claim_id"]: row
        for row in rows
        if row["expected_support"] == "unsupported"
    }
    if set(positives) != set(negatives):
        raise AssertionError("expected one positive and one negative for each claim_id")

    cache = build_cache(rows)
    cases = []
    lexical_detected = 0
    role_aware_detected = 0
    authority_role_rescues = []
    spurious_identity_regressions = []

    for claim_id in sorted(positives):
        baseline = evidence(positives[claim_id], cache)
        candidate = evidence(negatives[claim_id], cache)

        lexical_regression = (
            baseline["score"] >= LEXICAL_THRESHOLD
            and candidate["score"] < LEXICAL_THRESHOLD
        )
        if lexical_regression:
            lexical_detected += 1

        combined = classify_evidence_transition(
            baseline_score=baseline["score"],
            candidate_score=candidate["score"],
            baseline_role=baseline["role"],
            candidate_role=candidate["role"],
            lexical_threshold=LEXICAL_THRESHOLD,
        )
        if combined["classification"] == "REGRESSION":
            role_aware_detected += 1
            if not lexical_regression and combined["reason"] == "authority_role":
                authority_role_rescues.append(claim_id)

        identity = classify_evidence_transition(
            baseline_score=baseline["score"],
            candidate_score=baseline["score"],
            baseline_role=baseline["role"],
            candidate_role=baseline["role"],
            lexical_threshold=LEXICAL_THRESHOLD,
        )
        if identity["classification"] == "REGRESSION":
            spurious_identity_regressions.append(claim_id)

        cases.append(
            {
                "claim_id": claim_id,
                "baseline": baseline,
                "candidate": candidate,
                "lexical_regression": lexical_regression,
                "combined": combined,
            }
        )

    return {
        "dataset": path,
        "claims": len(cases),
        "unique_citations": len(cache),
        "lexical_detected": lexical_detected,
        "role_aware_detected": role_aware_detected,
        "authority_role_rescues": authority_role_rescues,
        "spurious_identity_regressions": spurious_identity_regressions,
        "cases": cases,
    }


results = {
    "v0.5_development": run_dataset(
        "benchmarks/real-claim-citation-v0.5/pairs.jsonl"
    ),
    "v0.6_replay": run_dataset(
        "benchmarks/semantic-v0.6/heldout.jsonl"
    ),
}

v05 = results["v0.5_development"]
v06 = results["v0.6_replay"]

assert v05["claims"] == 10, v05
assert v05["lexical_detected"] == 9, v05
assert v05["role_aware_detected"] == 10, v05
assert v05["authority_role_rescues"] == ["C03"], v05
assert v05["spurious_identity_regressions"] == [], v05

assert v06["claims"] == 10, v06
assert v06["lexical_detected"] == 10, v06
assert v06["role_aware_detected"] == 10, v06
assert v06["spurious_identity_regressions"] == [], v06

Path("/tmp/v0.7-role-aware-report.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("V0.7 ROLE-AWARE DIFFERENTIAL BENCHMARK: PASS")
print(
    "V0.5 development: "
    f"lexical={v05['lexical_detected']}/10 "
    f"role-aware={v05['role_aware_detected']}/10 "
    f"rescued={v05['authority_role_rescues']}"
)
print(
    "V0.6 replay: "
    f"lexical={v06['lexical_detected']}/10 "
    f"role-aware={v06['role_aware_detected']}/10"
)
print(
    "identity controls: "
    f"v0.5={len(v05['spurious_identity_regressions'])} regressions "
    f"v0.6={len(v06['spurious_identity_regressions'])} regressions"
)

c03 = next(case for case in v05["cases"] if case["claim_id"] == "C03")
print(
    "C03 rescue: "
    f"{c03['baseline']['citation']} {c03['baseline']['role']} "
    f"score={c03['baseline']['score']:.3f} -> "
    f"{c03['candidate']['citation']} {c03['candidate']['role']} "
    f"score={c03['candidate']['score']:.3f} "
    f"reason={c03['combined']['reason']}"
)
