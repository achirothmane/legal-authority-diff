# V0.12 prediction freeze

These 20 predictions were committed before any `expected_relation` / gold-label
file was created for V0.12.

Prediction context provenance:

- GovInfo U.S. Reports source backend
- context workflow:
  https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35747500066
- context artifact digest:
  `sha256:4e4d3662f38ad394237287c32deb298561a2e3b1e01163b09e94ea127283bb21`
- selection rule: first normalized occurrence of `target_term`, radius 1,200
  characters.

No expected labels are present in `candidates.jsonl` or
`predictions.jsonl`.

Four cases (B05, B06, B07, B13) did not resolve the predeclared target term under
that fixed context rule, so their predictions are explicit low-confidence
abstentions rather than manually selecting a more favorable passage.

These predictions are not independently blinded in the clinical-study sense:
the same assistant selected the pairs and may have general legal background
knowledge. The purpose is to reduce direct label leakage before independent
adjudication, not to claim promotion-grade accuracy.
