from legal_authority_diff.authority_role import (
    classify_authority_role,
    compare_authority_roles,
)
from legal_authority_diff.benchmark import score_claim_against_source
from legal_authority_diff.govinfo import fetch_us_reports_text


def evidence(claim, citation):
    text, metadata = fetch_us_reports_text(citation)
    lexical = score_claim_against_source(claim, text)
    role = classify_authority_role(lexical["window"])
    return {
        "citation": citation,
        "lexical_score": lexical["score"],
        "window": lexical["window"],
        "role": role,
        "source": metadata,
    }


gideon_claim = (
    "An indigent criminal defendant charged with a felony has a right "
    "to appointed counsel in state court."
)
gideon = evidence(gideon_claim, "372 U.S. 335")
miranda = evidence(gideon_claim, "384 U.S. 436")
gideon_diff = compare_authority_roles(
    gideon["role"]["role"],
    miranda["role"]["role"],
)

assert gideon["role"]["role"] == "REPORTER_SYLLABUS_HOLDING", gideon
assert miranda["role"]["role"] == "SECONDARY_SOURCE", miranda
assert gideon_diff["classification"] == "REGRESSION", gideon_diff

kyllo_claim = (
    "Using sense-enhancing technology not in general public use to obtain "
    "information about the interior of a home that otherwise could not be "
    "obtained without physical intrusion is a Fourth Amendment search."
)
kyllo = evidence(kyllo_claim, "533 U.S. 27")
riley = evidence(kyllo_claim, "573 U.S. 373")
kyllo_diff = compare_authority_roles(
    kyllo["role"]["role"],
    riley["role"]["role"],
)

assert kyllo["role"]["role"] == "COURT_SELF_HOLDING", kyllo
assert kyllo_diff["classification"] != "REGRESSION", kyllo_diff

print("V0.7 AUTHORITY-ROLE PROVENANCE: PASS")
print(
    "Gideon -> Miranda: "
    f"{gideon['role']['role']} -> {miranda['role']['role']} "
    f"=> {gideon_diff['classification']}"
)
print(
    "Kyllo -> Riley: "
    f"{kyllo['role']['role']} -> {riley['role']['role']} "
    f"=> {kyllo_diff['classification']}"
)
print(
    "Gideon lexical scores: "
    f"baseline={gideon['lexical_score']:.3f} "
    f"candidate={miranda['lexical_score']:.3f}"
)
print(
    "Kyllo lexical scores: "
    f"baseline={kyllo['lexical_score']:.3f} "
    f"candidate={riley['lexical_score']:.3f}"
)
