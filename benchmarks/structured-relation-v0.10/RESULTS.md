# V0.10 structured relation extraction — result

First independent held-out run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35728903431

Development replay run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35727772444

Source backend: official GovInfo U.S. Reports PDFs.

## Hypothesis

V0.9 showed that target-scoped surface relation patterns fail when they cannot
separate:

1. the proposition being stated;
2. who owns or asserts that proposition;
3. the target authority;
4. the current court's treatment of that authority.

V0.10 tested a deterministic structured frame with explicit target resolution,
proposition attribution, current-court actions, and abstention.

The experiment was kept separate from the mandatory core gate.

## Development replay

V0.10 was first developed against the already-observed V0.9 set. This is not
held-out evidence.

Final development replay:

```text
V0.9:  11 / 20
V0.10: 15 / 20

fixed by V0.10: H08, H13, H14, H19
broken vs V0.9: none

AFFIRMATIVE_USE          6 / 7
DISTINGUISHES_OR_LIMITS  3 / 5
NEGATIVE_TREATMENT       4 / 4
MIXED_OR_CONFLICTING     0 / 2
MENTION_ONLY             1 / 1
UNKNOWN                  1 / 1
```

The most important development fix was H19. A sentence describing what Hildwin
itself held—containing the words "does not require"—was no longer mistaken for
the current court limiting Hildwin. The frame attributed that proposition to the
target authority and returned `MENTION_ONLY`.

## Frozen independent held-out set

A new 16-case set was then frozen before first execution. The extractor blob was
frozen as:

```text
b2e53647079bede921183514f0afff921d31ed44
```

Expected distribution:

```text
AFFIRMATIVE_USE          9
DISTINGUISHES_OR_LIMITS  4
NEGATIVE_TREATMENT       1
MENTION_ONLY             1
UNKNOWN                  1
```

Predeclared criteria for advancing:

- resolved accuracy >= 0.75;
- V0.10 not worse than V0.9 on the same resolved rows;
- the historical target-holding attribution trap must remain safe;
- at most one high-confidence wrong prediction.

## First held-out result

```text
raw accuracy:
V0.9  = 0.500
V0.10 = 0.500

resolved accuracy:
V0.9  = 0.500
V0.10 = 0.500

pairs = 16
GOLD_SUSPECT = 0
high-confidence wrong = 1
```

By class:

```text
AFFIRMATIVE_USE          5 / 9
DISTINGUISHES_OR_LIMITS  0 / 4
NEGATIVE_TREATMENT       1 / 1
MENTION_ONLY             1 / 1
UNKNOWN                  1 / 1
```

V0.10 therefore failed the predeclared 0.75 resolved-accuracy criterion and did
not improve over V0.9 on independent held-out data.

The attribution-trap criterion did pass, and only one resolved error was
high-confidence. Those are useful partial results, but not enough to advance the
deterministic extractor.

## Important semantic failure

The one high-confidence wrong prediction was `S10`, Fernandez v. California
relative to Georgia v. Randolph.

Expected:

```text
DISTINGUISHES_OR_LIMITS
```

V0.10 predicted:

```text
AFFIRMATIVE_USE
confidence=high
```

The passage frames the question whether Randolph applies and then expressly
refuses to extend Randolph to the different situation before the Court. The
deterministic action linker treated the nearby "applies" framing as affirmative
use.

This shows that even after proposition ownership is separated, legal relation
classification still needs discourse/argument structure: a question about
whether precedent applies is not itself an application of precedent.

## Other held-out misses

```text
S01 Terry / Navarette:
implicit application -> MENTION_ONLY

S02 Batson / Foster:
framework application -> MENTION_ONLY

S04 Taylor / Mathis:
precedent resolves case -> MENTION_ONLY

S08 Brulotte / Kimble:
declines to overrule -> MENTION_ONLY

S11 Caplin / Luis:
fact/property distinction -> MENTION_ONLY

S12 Johnson / Beckles:
different legal setting -> MENTION_ONLY

S13 Tanner / Pena-Rodriguez:
multi-authority "unlike" clause -> MENTION_ONLY
```

There were no target-resolution GOLD_SUSPECT rows in the independent held-out
run, so these failures cannot be dismissed as source-acquisition errors.

## Falsification result

The hypothesis

> a deterministic structured frame plus hand-authored treatment patterns is
> sufficient to generalize precedent-relation extraction

is **not supported** by the held-out experiment.

We do not tune new rules on these held-out misses.

## Decision

V0.10 is not promoted into the mandatory core gate.

The experiment is isolated in:

```text
src/legal_authority_diff/structured_relation_v010.py
```

The V0.8 experimental relation path remains unchanged.

The next test should replace hand-authored relation classification with a
schema-constrained structured extractor that can model discourse roles directly,
for example:

```text
target_authority
proposition
proposition_owner
current_court_stance
treatment
claim_consequence
evidence_span
confidence / abstain
```

Before any such model is trusted, a small attorney-adjudicated subset should be
created so that the next benchmark does not rely only on engineering labels.

This software remains experimental and is not legal advice.

## Reproducibility note

The exact first-heldout extractor is preserved as:

`src/legal_authority_diff/structured_relation_v010_frozen.py`

After the held-out result was recorded, the working experimental module received one narrow fix required by a unit test that predated the held-out run: a `we overrule ... TARGET` matcher may not cross a sentence boundary and accidentally attach an overruling of another case to the target. The first-heldout score was not rerun or replaced after that fix; the held-out runner is pinned to the frozen snapshot above.
