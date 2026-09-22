# V0.8 authority relationship challenge — result

Measured run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35722812150

Source backend: official GovInfo U.S. Reports PDFs.

## Why V0.8 exists

V0.7 showed that authority-role provenance can recover a lexical false positive,
but it also exposed a new risk: a later opinion may legitimately apply or reaffirm
an earlier precedent while the local text still looks like attributed prior
authority.

A release gate must not block that merely because the candidate is a later case.

V0.8 therefore separates two questions:

1. what role the retrieved evidence window plays; and
2. how the current source locally treats a specific earlier authority.

The relation labels are:

- `AFFIRMATIVE_USE`
- `DISTINGUISHES_OR_LIMITS`
- `NEGATIVE_TREATMENT`
- `MENTION_ONLY`
- `UNKNOWN`

This is a local textual relationship signal, not a full citator and not a
current-law determination.

## Frozen challenge set

The benchmark contains 12 fixed local challenges from U.S. Supreme Court
opinions:

```text
AFFIRMATIVE_USE          5
DISTINGUISHES_OR_LIMITS  2
NEGATIVE_TREATMENT       1
MENTION_ONLY             3
UNKNOWN                  1
```

Examples include later opinions applying/reaffirming Miranda, Terry,
Strickland, Daubert, and Batson; distinguishing/limiting Crawford and Edwards;
and expressly overruling Michigan v. Jackson.

## First execution

The first frozen run scored:

```text
11 / 12
accuracy = 0.917
```

The only miss was `R05`, not a relation-classification error. GovInfo PDF text
split the word `Batson` as `Ba tson`, so the fixed benchmark anchor could not
be located:

```text
R05
expected = AFFIRMATIVE_USE
predicted = UNKNOWN
reason = anchor_not_found
```

The labels, source citation, target citation, anchor text, relation rules, and
challenge membership were not changed. A generic OCR-tolerant anchor resolver
was added to tolerate whitespace inserted inside words.

## Re-run after source-normalization fix

```text
correct = 12 / 12
accuracy = 1.000

AFFIRMATIVE_USE          5 / 5
DISTINGUISHES_OR_LIMITS  2 / 2
NEGATIVE_TREATMENT       1 / 1
MENTION_ONLY             3 / 3
UNKNOWN                  1 / 1
```

Because the source-normalization fix was made after observing the first run,
the 12/12 result is a corrected replay, not a pristine untouched held-out score.

## Relation-aware policy experiment

V0.8 also tests the policy consequence of these relationship classes.

For the five real `AFFIRMATIVE_USE` challenges, the policy benchmark isolates
the false-block scenario with synthetic above-threshold support scores and a
role-only downgrade:

```text
baseline role:  COURT_SELF_HOLDING
candidate role: ATTRIBUTED_PRIOR_AUTHORITY

V0.7 role-only policy: REGRESSION
V0.8 with AFFIRMATIVE_USE: NO_REGRESSION_DETECTED
```

Measured policy result:

```text
affirmative-use role-only false blocks prevented = 5 / 5
negative-treatment mapped to WORLD_CHANGE        = 1 / 1
distinguish/limit mapped to UNKNOWN               = 2 / 2
```

An `AFFIRMATIVE_USE` relation does **not** rescue a candidate that falls below
the frozen lexical support threshold. It only prevents the authority-role signal
from creating a false block by itself.

`NEGATIVE_TREATMENT` routes to `WORLD_CHANGE`, because an explicit later
overruling is a change in the legal world rather than evidence that the AI system
itself regressed.

`DISTINGUISHES_OR_LIMITS` routes to `UNKNOWN`, because the consequence
depends on the exact proposition and facts.

## Decision

V0.8 supports keeping precedent relationship as a separate evidence axis.

It is not yet promoted into the mandatory core gate. The benchmark is small,
engineering-labeled, and focused on explicit textual cues.

The next falsification requirement should be a larger held-out set constructed
without tuning against these 12 examples, especially:

- later cases that apply precedent without explicit words such as "applies";
- mixed passages that both quote and distinguish an authority;
- negative treatment short of overruling;
- false-positive controls containing relation words about a different case;
- attorney-adjudicated labels for a smaller high-value subset.

This software remains experimental and is not legal advice.
