# Independent Reviewer Brief — V0.12 Blind Legal-Relation Benchmark

## Purpose

We are evaluating an experimental open-source tool that detects changes in legal
authority support across AI-system versions.

This review is **not legal advice** and does not concern a live client's legal
matter. The task is benchmark annotation of U.S. Supreme Court opinion passages.

## What the reviewer sees

For each case pair, the blind packet provides:

- source case and citation;
- target precedent and citation;
- a mechanically selected passage from the source opinion;
- blank review fields.

The packet deliberately omits the tool's frozen prediction.

## Review task

For each row, assign exactly one treatment label:

- `AFFIRMATIVE_USE` — the current court applies, relies on, reaffirms, adopts,
  or expressly keeps the target precedent.
- `DISTINGUISHES_OR_LIMITS` — the current court distinguishes the target,
  refuses to extend it, or limits its reach.
- `NEGATIVE_TREATMENT` — the current court overrules, materially weakens, or
  expressly disapproves the target.
- `MENTION_ONLY` — the passage quotes, cites, or describes the target without
  itself applying, limiting, or rejecting it.
- `UNKNOWN` — the passage is insufficient, the target is unresolved, or the
  treatment cannot be determined reliably.

Also provide:

- confidence: `low`, `medium`, or `high`;
- one short verbatim evidence span for every non-`UNKNOWN` label;
- optional notes when the passage is ambiguous or defective;
- reviewer role (for example: U.S. attorney, law graduate, J.D. student).

## Important anti-leakage rule

Do **not** inspect:

`benchmarks/blinded-relation-v0.12/predictions.jsonl`

before committing your labels.

The prediction file was frozen before adjudication. Seeing it would invalidate
the blind comparison.

## Scope

Please judge only the treatment shown in the supplied passage. Do not use
outside knowledge to "correct" the passage unless your note explicitly says the
packet is defective.

For rows marked `TARGET_TERM_NOT_FOUND`, do not search for another passage.
The source-selection failure is part of the benchmark.

## Time

A 5-case subset should take roughly 15–30 minutes for a legally trained reviewer.
A full 20-case review can be split among multiple reviewers.

## Independence

A reviewer who has not seen the frozen predictions is useful for evaluation.
For promotion-grade evidence, a U.S.-law-trained reviewer or advanced U.S. law
student is preferred.

Thank you for helping test an open-source legal-AI reliability tool.
