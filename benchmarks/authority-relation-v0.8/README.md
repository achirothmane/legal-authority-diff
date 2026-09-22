# V0.8 authority relationship challenge set

V0.8 is independent from the V0.5/V0.6 claim-citation score tuning loop.

It tests a different question:

> When a later opinion mentions an earlier authority, can the tool distinguish
> affirmative use from distinction/limitation, negative treatment, mere mention,
> and absence?

The set contains 12 fixed local challenges from official U.S. Reports PDFs:

- 5 affirmative-use examples;
- 2 distinguish/limit examples;
- 1 explicit negative-treatment example;
- 3 mention-only examples;
- 1 target-absent UNKNOWN control.

Each row fixes a source citation, target citation, local anchor, and context radius
before the classifier is evaluated. The benchmark is about local textual
relationship cues, not a complete citator or a current-law determination.

The source opinions are fetched from GovInfo. Benchmark labels are engineering
labels and are not attorney-adjudicated legal advice.
