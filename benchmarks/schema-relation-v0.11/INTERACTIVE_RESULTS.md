# V0.11 interactive development replay — result

Run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35745115142

## Status

This was a **label-visible interactive development exercise** performed with
GPT-5.6 Sol inside ChatGPT after the V0.10 expected labels were already known.

It is **not**:

- a model-accuracy benchmark;
- a live OpenAI API run;
- held-out evidence;
- promotion evidence for the V0.11 extractor.

No paid API credits were used.

## What was tested

Sixteen structured extraction records were authored against the already-observed
V0.10 cases, then validated by repository code against source contexts rebuilt
from official GovInfo U.S. Reports PDFs.

The free validation checked:

- exact schema validity;
- target citation identity;
- deterministic stance -> treatment consistency;
- verbatim evidence grounding in the source context;
- abstention invariants;
- intended treatment fit to the already-known development labels.

## Result

```text
schema_valid             = 16 / 16
intended_label_fit       = 16 / 16
usable_for_policy        = 15 / 16
validated_abstentions    = 1
```

The only unusable record was the intended unresolved-target control:

```text
S16
expected = UNKNOWN
validated treatment = UNKNOWN
valid schema = true
usable = false
evidence spans = 0
```

That is the desired fail-open behavior.

All 15 non-abstaining records contained grounded evidence spans and passed the
deterministic validator.

## Interpretation

The result proves a narrow engineering point:

> the V0.11 schema and validator are expressive enough to represent all 16
> already-known development interpretations while enforcing grounded evidence
> and fail-open abstention.

It does **not** show that a model can independently infer those structures from
unseen legal passages.

Because the labels were visible when the records were authored, 16/16 must not
be reported as V0.11 predictive accuracy.

## Next evidence requirement

Before any promotion claim:

1. freeze the V0.11 schema, prompt, validator, policy bridge, model configuration,
   and source-context builder;
2. construct a new unseen relation set not used in V0.8–V0.11 development;
3. obtain independent legal review for a small adjudication subset;
4. predeclare success and abstention thresholds;
5. run the frozen extractor once using a reproducible model/API path when credits
   are available.

This software remains experimental and is not legal advice.
