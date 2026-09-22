# V0.11 schema-constrained relation extraction

V0.10 falsified the hypothesis that deterministic discourse frames plus
hand-authored treatment patterns were enough to generalize precedent-relation
classification.

V0.11 changes the architecture instead of adding more regex rules.

## Architecture

```text
source passage
  -> schema-constrained extractor
  -> strict schema validation
  -> target identity check
  -> evidence grounding check
  -> deterministic stance -> treatment mapping
  -> experimental relation-aware policy
  -> BLOCK / WORLD_CHANGE / UNKNOWN / no regression
```

The model is not allowed to emit the CI verdict.

The extraction schema contains:

```text
target_authority
proposition
proposition_owner
current_court_stance
treatment
claim_consequence
evidence_spans
confidence
abstain
abstention_reason
```

## Safety invariants

- invalid schema -> `UNKNOWN`;
- fabricated or ungrounded evidence span -> `UNKNOWN`;
- target citation mismatch -> `UNKNOWN`;
- stance/treatment disagreement -> `UNKNOWN`;
- explicit model abstention -> `UNKNOWN`;
- unresolved target -> `UNKNOWN`;
- only validated, grounded, non-abstaining treatment reaches the experimental
  policy layer.

A model output therefore cannot become blocking merely because it looks
plausible.

## Development replay

The manual workflow `schema-relation-v0.11-dev` uses the already-observed
V0.10 16-case set. This is intentionally **development data**, not held-out
evidence for V0.11.

The workflow requires an Actions secret named:

```text
OPENAI_API_KEY
```

It uses:

```text
model: gpt-5.6-sol
reasoning effort: medium
store: false
Structured Outputs: strict JSON schema
```

The run records the prompt hash, schema hash, requested model, provider-returned
model identity, validation errors, abstentions, evidence spans, and every
prediction.

## Promotion protocol

Do not promote V0.11 on the development replay.

After the prompt and schema stabilize:

1. freeze prompt, schema, model configuration, and source-context builder;
2. create a new independent held-out relation set that was not used in V0.8,
   V0.9, V0.10, or the V0.11 development replay;
3. include implicit application, refuses-to-extend, fact distinctions, negative
   treatment, historical target propositions, multi-authority passages, and
   target-absent controls;
4. obtain independent legal review for a small adjudication subset before
   treating the labels as promotion-grade ground truth;
5. predeclare thresholds before the first held-out model call.

The next held-out threshold is intentionally not set in this development PR.
It must be frozen together with the new unseen set before execution.

This experiment is not legal advice.
