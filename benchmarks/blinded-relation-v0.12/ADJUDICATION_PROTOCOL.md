# V0.12 blind adjudication protocol

The prediction freeze and adjudication must remain separated.

## Prediction side

Frozen predictions live in:

`benchmarks/blinded-relation-v0.12/predictions.jsonl`

They were created before any V0.12 gold-label file.

## Reviewer side

Build the blind packet with:

```bash
python scripts/build_v012_blind_adjudication_packet.py
```

The resulting file contains source/target identity and the mechanically selected
GovInfo passage, but **does not contain the frozen V0.12 prediction**.

A reviewer should assign exactly one treatment:

- `AFFIRMATIVE_USE`
- `DISTINGUISHES_OR_LIMITS`
- `NEGATIVE_TREATMENT`
- `MENTION_ONLY`
- `UNKNOWN`

The reviewer should also provide:

- confidence: low / medium / high;
- one verbatim evidence span when a non-UNKNOWN label is assigned;
- notes for ambiguity or source/context defects;
- reviewer identifier or role.

For a `TARGET_TERM_NOT_FOUND` passage, the reviewer should not search for a
different passage. The context-selection failure itself must remain visible.

## Independence rule

The reviewer must not inspect `predictions.jsonl` before committing the gold
labels.

An adjudication file should be added only after the prediction-freeze commit is
identified in the result notes.

A review performed by the same assistant that authored the predictions is not
independent and must not be presented as promotion-grade ground truth.
