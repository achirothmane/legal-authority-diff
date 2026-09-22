# V0.7 authority-role provenance — result

Live run:
https://github.com/othy19904-eng/legal-authority-diff/actions/runs/35721271909

Source backend: official GovInfo U.S. Reports PDFs.

## Hypothesis

A legal regression can survive a lexical support threshold when the candidate
source contains highly related language that is playing the wrong evidentiary
role—for example secondary material quoted inside an opinion rather than the
source case's own holding/rule language.

V0.7 tests whether a conservative provenance signal can catch that failure
without replacing the existing lexical evidence layer.

## Observable roles

The experimental classifier only uses explicit textual cues and can return:

- `COURT_SELF_HOLDING`
- `REPORTER_SYLLABUS_HOLDING`
- `ATTRIBUTED_PRIOR_AUTHORITY`
- `SECONDARY_SOURCE`
- `UNKNOWN`

Important: the U.S. Reports syllabus is prepared by the Reporter of Decisions and
is not part of the Court's opinion. V0.7 therefore keeps
`REPORTER_SYLLABUS_HOLDING` separate from `COURT_SELF_HOLDING`.

## Development failure recovered

The V0.5 false positive was the Gideon appointed-counsel proposition paired with
Miranda.

```text
baseline:
372 U.S. 335 — Gideon v. Wainwright
lexical score: 0.478
role: REPORTER_SYLLABUS_HOLDING

candidate:
384 U.S. 436 — Miranda v. Arizona
lexical score: 0.365
role: SECONDARY_SOURCE
```

Both sides clear the frozen V0.5 lexical threshold of `0.34`, so lexical
support alone accepts the candidate. The candidate's best evidence window is
from a law-review citation embedded in the Miranda source material.

V0.7 therefore adds:

```text
REPORTER_SYLLABUS_HOLDING -> SECONDARY_SOURCE
reason: authority_role
classification: REGRESSION
```

## Paired benchmark

The 10 positive/negative claim pairs from V0.5 were replayed as differential
tests: positive citation as baseline, hard-negative citation as candidate.

```text
V0.5 development
lexical-only regressions detected: 9/10
role-aware regressions detected: 10/10
rescued by authority role: C03 only
identity-control regressions: 0
```

The same differential policy was replayed on the V0.6 10-claim set:

```text
V0.6 replay
lexical-only regressions detected: 10/10
role-aware regressions detected: 10/10
identity-control regressions: 0
```

The V0.6 replay is not claimed as a new untouched held-out result; that set was
already observed during V0.6.

## Conservative controls and limits

V0.7 deliberately refuses to force uncertain role transitions into a failure.

```text
Kyllo -> Riley:
COURT_SELF_HOLDING -> UNKNOWN
classification: UNKNOWN
```

Additional probes expose an important limitation of the current heuristic:

```text
Mapp -> Miranda:
ATTRIBUTED_PRIOR_AUTHORITY -> SECONDARY_SOURCE
classification: UNKNOWN

Tinker -> T.L.O.:
ATTRIBUTED_PRIOR_AUTHORITY -> ATTRIBUTED_PRIOR_AUTHORITY
classification: UNCHANGED
```

Those baseline role labels show that selecting one lexical evidence window is
not sufficient to reconstruct every case's holding provenance. V0.7 is therefore
an additive high-confidence signal, not a general holding detector.

## Decision

Promote the **concept** of authority-role provenance to the next falsification
stage, but do not make this heuristic a mandatory core gate yet.

The next evidence requirement is a new authority-role challenge set containing
cases where a later opinion quotes, discusses, distinguishes, or applies the
true originating authority. That set should be labeled independently of the
V0.5/V0.6 development examples and should measure:

- primary-holding -> quoted-prior-authority downgrades;
- primary-holding -> secondary-source downgrades;
- legitimate later applications/reaffirmations that must not be falsely blocked;
- UNKNOWN coverage and abstention quality.

This software remains experimental and is not legal advice.
