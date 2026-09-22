# V0.12 blinded prediction freeze

This stage is deliberately **unlabeled**.

The 20 source/target pairs in `candidates.jsonl` were frozen before any V0.12
gold labels were created. The file contains no expected treatment field.

Context selection is also predeclared:

- locate the first normalized occurrence of `target_term` in the GovInfo
  U.S. Reports text;
- take a fixed 1,200-character radius around that occurrence;
- do not choose a different passage because it makes a prediction easier.

The next step is to author and freeze one V0.11-schema prediction for each
context **without adding gold labels**.

Only after predictions are committed will an adjudication packet be created.
Gold labels must live in a separate later commit/file.

Important limitation: the same assistant selected the source/target pairs and
may have background legal knowledge. Therefore this is a leakage-reduction
protocol, not a fully independent blinded study.

Promotion-grade evidence still requires independent legal adjudication.
