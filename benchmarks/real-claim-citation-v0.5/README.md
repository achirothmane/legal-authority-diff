# Real claim-citation benchmark V0.5

This dataset contains 20 claim-citation pairs:

- 10 positive pairs where the cited U.S. Supreme Court opinion is expected to support the proposition.
- 10 hard negative pairs that reuse the same claims but pair them with real opinions on nearby legal topics.

The benchmark measures **source proposition support**, not whether a proposition is current law today.

The negative set is intentionally difficult for topic-only similarity. Examples include:

- Miranda claim vs. Gideon (criminal procedure / counsel overlap)
- Gideon claim vs. Miranda
- Tinker claim vs. T.L.O. (school context overlap)
- Brandenburg claim vs. Sullivan (First Amendment overlap)
- Obergefell claim vs. Loving (marriage overlap)
- T.L.O. claim vs. Mapp (search doctrine overlap)

V0.5 begins with a deterministic lexical-retrieval baseline. The point is to measure false positives and false negatives before adding embeddings, NLI, or an LLM judge.

Run live:

```bash
export COURTLISTENER_TOKEN="..."
legal-benchmark-support \
  benchmarks/real-claim-citation-v0.5/pairs.jsonl \
  --output /tmp/v0.5-report.json
```

A benchmark label is a test fixture for this experimental engineering project, not legal advice.


## Source backend

The reproducible V0.5 run uses official GovInfo U.S. Reports PDFs rather than a
third-party case-law API. This separates **source acquisition** from the
**support verifier** and avoids making benchmark results depend on CourtListener
account quotas.

Install the benchmark extra before running:

```bash
python -m pip install -e ".[benchmark]"
legal-benchmark-support \
  benchmarks/real-claim-citation-v0.5/pairs.jsonl \
  --source govinfo \
  --output /tmp/v0.5-report.json
```

CourtListener remains available as an optional source backend for comparison.
