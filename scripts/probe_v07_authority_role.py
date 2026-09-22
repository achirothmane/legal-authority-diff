from legal_authority_diff.benchmark import score_claim_against_source
from legal_authority_diff.govinfo import fetch_us_reports_text

CASES = [
    (
        "NEG003_MIRANDA",
        "An indigent criminal defendant charged with a felony has a right to appointed counsel in state court.",
        "384 U.S. 436",
    ),
    (
        "POS_GIDEON",
        "An indigent criminal defendant charged with a felony has a right to appointed counsel in state court.",
        "372 U.S. 335",
    ),
    (
        "NEG010_RILEY",
        "Using sense-enhancing technology not in general public use to obtain information about the interior of a home that otherwise could not be obtained without physical intrusion is a Fourth Amendment search.",
        "573 U.S. 373",
    ),
    (
        "POS_KYLLO",
        "Using sense-enhancing technology not in general public use to obtain information about the interior of a home that otherwise could not be obtained without physical intrusion is a Fourth Amendment search.",
        "533 U.S. 27",
    ),
]

for label, claim, citation in CASES:
    text, _ = fetch_us_reports_text(citation)
    result = score_claim_against_source(claim, text)
    print("=" * 80)
    print(label)
    print(citation)
    print("score:", result["score"])
    print(result["window"])
