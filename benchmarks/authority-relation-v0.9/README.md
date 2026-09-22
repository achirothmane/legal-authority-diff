# V0.9 authority-relation held-out benchmark

This benchmark is frozen before its first execution.

It contains 20 local precedent-relationship challenges from official U.S. Reports
opinions that were not used as the V0.8 12-case relation benchmark.

The benchmark deliberately targets harder failure modes:

- implicit application without a literal `applies` or `reaffirms`;
- negative treatment short of express overruling;
- fact-specific limitation of earlier precedent;
- relation words concerning a different nearby authority;
- passages that preserve one part of a precedent while limiting another;
- a target-absent UNKNOWN control.

Expected label distribution:

- `AFFIRMATIVE_USE`: 7
- `DISTINGUISHES_OR_LIMITS`: 5
- `NEGATIVE_TREATMENT`: 4
- `MIXED_OR_CONFLICTING`: 2
- `MENTION_ONLY`: 1
- `UNKNOWN`: 1

The source backend is GovInfo U.S. Reports PDF text.

Protocol:

1. Freeze challenge membership, source/target citations, anchors, radii, and labels.
2. Run the current V0.9 classifier once.
3. Record the first-run result without tuning on misses.
4. Infrastructure-only source extraction fixes may be replayed, but must be labeled
   as replays and may not change relation rules or expected labels.

These are engineering benchmark labels, not attorney-adjudicated legal advice.
