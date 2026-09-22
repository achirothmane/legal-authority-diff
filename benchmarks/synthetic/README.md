# Synthetic falsification suite

This suite contains **30 intentionally synthetic cases**. It tests the differential engine itself and does not assert anything about real law.

Expected outcomes:

- 20 `REGRESSION`
- 2 `IMPROVEMENT`
- 2 `UNCHANGED`
- 3 `UNKNOWN`
- 3 `WORLD_CHANGE`
- overall decision: `BLOCK`

The regression cases cover four V0.1 failure classes:

1. citation existence loss;
2. authority-strength downgrade;
3. negative treatment;
4. proposition-support downgrade.

The suite also checks that the engine does **not** overclaim when the world changes or when jurisdictional equivalence cannot be determined from supplied metadata.

Run it with:

```bash
legal-diff benchmarks/synthetic/baseline.jsonl benchmarks/synthetic/candidate.jsonl
```

This is a falsification harness, not a legal benchmark.
