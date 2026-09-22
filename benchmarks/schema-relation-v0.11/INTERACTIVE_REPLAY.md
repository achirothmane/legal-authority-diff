# V0.11 interactive development replay

This file is **not a benchmark of model accuracy**.

The 16 cases come from the already-observed V0.10 dataset, and their expected
labels are visible in the repository. The extraction records were authored
interactively with GPT-5.6 Sol inside ChatGPT after those labels were already
known.

The purpose is narrower:

- verify that the V0.11 schema can express the intended legal discourse
  distinctions;
- verify that evidence spans are actually grounded in the official-source
  context reconstructed from GovInfo;
- exercise stance -> treatment mapping;
- exercise fail-open handling for the unresolved target control;
- identify schema or validator defects without spending API credits.

Therefore even a 16/16 label fit would **not** be promotion evidence and must not
be reported as held-out accuracy.

The next promotion-grade step still requires a newly frozen unseen set and
independent legal review for at least a small adjudication subset.
