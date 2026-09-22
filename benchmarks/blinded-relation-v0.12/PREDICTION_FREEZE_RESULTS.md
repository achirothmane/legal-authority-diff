# V0.12 prediction freeze — result

Prediction commit created before any V0.12 gold-label file:

`bb18669692069de81ba037ba0f1643610ea4d037`

No `expected_relation` field exists in the V0.12 candidate or prediction files.

## Context freeze

Context workflow:

https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35747500066

Artifact digest:

`sha256:4e4d3662f38ad394237287c32deb298561a2e3b1e01163b09e94ea127283bb21`

Context rule was frozen before prediction:

- first normalized occurrence of `target_term`;
- fixed radius: 1,200 characters;
- GovInfo U.S. Reports text;
- no manual passage substitution.

Four rows did not resolve the predeclared target term:

```text
B05
B06
B07
B13
```

Those rows were preserved as source-selection failures and predicted as explicit
low-confidence `UNKNOWN` abstentions. No alternate passage was chosen.

## Prediction freeze

Frozen distribution:

```text
AFFIRMATIVE_USE          11
DISTINGUISHES_OR_LIMITS   2
NEGATIVE_TREATMENT        1
MENTION_ONLY              2
UNKNOWN                    4
TOTAL                     20
```

## Deterministic validation

Validation and blind-packet workflow:

https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35748017302

Result:

```text
schema_valid        = 20 / 20
usable              = 16 / 20
abstentions         = 4
unresolved_contexts = 4
```

All 16 non-abstaining predictions passed target identity, stance/treatment
consistency, and verbatim evidence-grounding checks.

The four unresolved contexts validate as non-usable abstentions rather than being
silently promoted into policy input.

Prediction-freeze artifact digest:

`sha256:10fd5fff6978970375f8a26c0e9314b341e652b52e6f38538a307d66e9f998c0`

## Blind adjudication packet

The same workflow builds:

`/tmp/v0.12-blind-adjudication-packet.jsonl`

The packet contains:

- source case and citation;
- target case and citation;
- mechanically selected context;
- blank review fields.

It deliberately omits all frozen prediction fields.

A reviewer should not inspect
`benchmarks/blinded-relation-v0.12/predictions.jsonl` before committing the gold
labels.

## What this proves

The project now has a concrete prediction-before-label pipeline with a verifiable
commit boundary. It reduces direct answer leakage relative to V0.11's
label-visible development replay.

It does **not** make the study independently blinded because the same assistant
selected the pairs and may possess background legal knowledge.

No V0.12 accuracy is reported yet because no independent gold labels exist.

## Next gate

Do not create a V0.12 accuracy result until a blind reviewer has adjudicated the
packet.

Promotion-grade evidence should preferably include legal-domain review for at
least a high-value subset.

This software remains experimental and is not legal advice.
