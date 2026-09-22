# V0.10 structured relation held-out benchmark

This 16-case benchmark is frozen before its first execution against the V0.10
structured extractor.

The extractor implementation is frozen at blob:

`src/legal_authority_diff/structured_relation.py`
`b2e53647079bede921183514f0afff921d31ed44`

The cases were selected from independent U.S. Supreme Court opinions that were
not used in the V0.9 20-case development replay.

Expected distribution:

```text
AFFIRMATIVE_USE          9
DISTINGUISHES_OR_LIMITS  4
NEGATIVE_TREATMENT       1
MENTION_ONLY             1
UNKNOWN                  1
```

The set deliberately includes:

- implicit and explicit precedent application;
- adherence to precedent after a request to overrule it;
- refusal to extend and fact/context distinctions;
- one explicit overruling;
- one historical statement of what the target precedent itself held;
- one target-absent control with other legal authority language nearby.

## Frozen evaluation protocol

The first run must report both V0.9 and V0.10 on the same target-aware source
context.

A row is flagged `GOLD_SUSPECT` before scoring consequences when:

- its expected label is not `UNKNOWN`; and
- the full target case name/citation cannot be resolved within the predeclared
  target-search distance around the anchor.

Such rows remain in raw accuracy. A separate resolved accuracy excludes them so
source/label problems are visible rather than silently converted into model
errors.

Predeclared success criteria for advancing V0.10 to another falsification stage:

1. resolved accuracy >= 0.75;
2. V0.10 resolved accuracy is not lower than V0.9 on the same rows;
3. the attributed-target-holding trap (`S15`) is not misclassified as current
   court negative/limiting treatment;
4. no more than one high-confidence wrong prediction on resolved rows.

Passing these criteria is not sufficient for promotion into the mandatory core
gate. It only justifies a larger benchmark and independent legal review.

No relation rule, expected label, challenge membership, anchor, radius, or target
identity may be changed after the first run to improve the score. Generic
source-acquisition fixes may be replayed only if clearly labeled as replays.

Engineering labels are not attorney-adjudicated legal advice.
