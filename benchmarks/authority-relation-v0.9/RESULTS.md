# V0.9 authority-relation held-out — result

First frozen run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35725486526

Corrected source-acquisition replay:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35725696246

Source backend: official GovInfo U.S. Reports PDFs.

## Hypothesis

V0.8 succeeded on a small set of explicit relationship cues. V0.9 tests whether
a stricter target-scoped regex approach generalizes to harder precedent
relationships without being fooled by relation words about a different case.

The 20-case set was frozen before its first execution. It includes implicit
application, fact-specific limitation, negative treatment short of overruling,
mixed passages, nearby relation words about other authorities, a local
mention-only control, and a target-absent UNKNOWN control.

Expected distribution:

```text
AFFIRMATIVE_USE          7
DISTINGUISHES_OR_LIMITS  5
NEGATIVE_TREATMENT       4
MIXED_OR_CONFLICTING     2
MENTION_ONLY             1
UNKNOWN                  1
```

## First frozen execution

```text
correct = 9 / 20
accuracy = 0.450
anchor failures = 3

AFFIRMATIVE_USE          5 / 7
DISTINGUISHES_OR_LIMITS  1 / 5
NEGATIVE_TREATMENT       2 / 4
MIXED_OR_CONFLICTING     0 / 2
MENTION_ONLY             0 / 1
UNKNOWN                  1 / 1
```

The three source-anchor failures were `H01`, `H15`, and `H19`.

No relation labels or relation-classification rules were changed after observing
this run.

## Infrastructure-only correction

A generic approximate anchor resolver was added for PDF extraction differences.
It uses token overlap plus sequence similarity only when exact and OCR-tolerant
anchor matching fail.

The held-out membership, labels, source/target citations, anchors, radii, and
relation rules remained unchanged.

Corrected replay:

```text
correct = 11 / 20
accuracy = 0.550
anchor failures = 0

AFFIRMATIVE_USE          6 / 7
DISTINGUISHES_OR_LIMITS  2 / 5
NEGATIVE_TREATMENT       2 / 4
MIXED_OR_CONFLICTING     0 / 2
MENTION_ONLY             0 / 1
UNKNOWN                  1 / 1
```

Because the anchor resolver was added after the first run, 11/20 is a corrected
replay, not an untouched held-out score.

## Semantic misses preserved

After source acquisition was fixed, nine relation errors remained:

```text
H07 implicit application near an overrule of another case
     expected AFFIRMATIVE_USE
     predicted MENTION_ONLY

H08 fact-specific limitation without a literal distinguish word
     expected DISTINGUISHES_OR_LIMITS
     predicted UNKNOWN

H10 "provides no support" limitation
     expected DISTINGUISHES_OR_LIMITS
     predicted UNKNOWN

H13 joint overruling language
     expected NEGATIVE_TREATMENT
     predicted MENTION_ONLY

H14 "no longer good law" through a longer coordinated clause
     expected NEGATIVE_TREATMENT
     predicted MENTION_ONLY

H16 precedent preserved in one sense and limited in another
     expected MIXED_OR_CONFLICTING
     predicted MENTION_ONLY

H17 target quoted and then its broad reading limited
     expected MIXED_OR_CONFLICTING
     predicted MENTION_ONLY

H18 related rule described as irrelevant to the present ground
     expected DISTINGUISHES_OR_LIMITS
     predicted MENTION_ONLY

H19 historical statement of what the target itself held
     expected MENTION_ONLY
     predicted DISTINGUISHES_OR_LIMITS
```

H19 is particularly important. The source says that the target case held that
the Sixth Amendment "does not require" something. A phrase-level classifier
mistook the **content of the target's holding** for the later court
**distinguishing or limiting the target**.

That failure is structural, not a threshold problem.

## Falsification result

The hypothesis

> target-scoped regex cues are sufficient to generalize V0.8 precedent
> relationship classification to harder legal passages

is **not supported**.

We do not add more regex rules based on these nine misses. Doing so would tune on
the held-out set and hide the actual failure.

## Engineering decision

The V0.8 relation classifier and V0.8 policy remain unchanged.

The V0.9 classifier and mixed-relation policy are isolated in:

```text
src/legal_authority_diff/authority_relation_v09.py
src/legal_authority_diff/relation_policy_v09.py
```

They are retained as falsification evidence and are not promoted into the
mandatory core gate.

The next experiment should stop adding surface patterns and instead test
structured relation extraction that separates:

1. the proposition stated in the passage;
2. who is asserting that proposition;
3. which authority the proposition is attributed to;
4. the current court's treatment of that authority;
5. whether the treatment changes the proposition actually under test.

A smaller attorney-adjudicated subset would materially improve the value of the
next benchmark.

This software remains experimental and is not legal advice.
