# V0.6 semantic support benchmark

This directory is intentionally separate from the V0.5 development benchmark.

`heldout.jsonl` contains 20 new claim-citation pairs built from 10 U.S. Supreme
Court opinions that do not appear in the V0.5 set:

- 10 positive proposition-support pairs;
- 10 topic-overlapping hard negatives.

The semantic verifier and its fixed decision threshold (`0.50`) are defined
before this held-out set is run. We do not tune the threshold or retrieval depth
against held-out outcomes.

The source backend is official GovInfo U.S. Reports PDFs.

The labels are engineering benchmark labels based on the cited opinions' widely
stated holdings. They have not been independently attorney-adjudicated and must
not be treated as legal advice or as a current-law validation set.

The V0.6 question is narrower:

> Can a local NLI entailment layer reduce topical false positives that fooled the
> lexical V0.5 baseline, without sacrificing supported claims?

The benchmark always reports both the frozen V0.5 lexical baseline and the V0.6
semantic verifier on the same held-out source text.
