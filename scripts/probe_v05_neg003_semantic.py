from legal_authority_diff.govinfo import fetch_us_reports_text
from legal_authority_diff.semantic import NliVerifier


claim = (
    "An indigent criminal defendant charged with a felony has a right "
    "to appointed counsel in state court."
)

source_text, metadata = fetch_us_reports_text("384 U.S. 436")
verifier = NliVerifier(
    model_name="cross-encoder/nli-MiniLM2-L6-H768",
    threshold=0.50,
    top_k=8,
    max_sentences=2,
)
decision = verifier.verify(claim, source_text)

print("V0.5 NEG-003 SEMANTIC PROBE")
print(f"citation: {metadata['citation']}")
print("expected: unsupported")
print(f"predicted: {decision['predicted_support']}")
print(f"entailment: {decision['nli']['entailment']:.3f}")
print(f"neutral: {decision['nli']['neutral']:.3f}")
print(f"contradiction: {decision['nli']['contradiction']:.3f}")
print(f"retrieval_score: {decision['retrieval_score']:.3f}")
