# Review benchmark: first baseline on the TEST split

BLUF: on 18 held-out real bug-fix cases, plain Sonnet and the Perun single pass are statistically indistinguishable on recall, and the seeded gap pass is the only configuration that moved recall (+0.17 absolute, 2.3x cost). Static tools found none of the bugs. n = 18 bugs, one run per arm per case: every difference below is inside the confidence interval.

## Setup
- Corpus: 26 real bug-fix cases from permissive-licence public repositories (MIT, BSD-3-Clause, Apache-2.0; shell 6, Python 7, JS 6, Go 7) plus the 6-bug held-out fixture from PR #1354 (27 cases, 32 bugs). Each case: the introducing commit's diff of the buggy file(s) as `change.patch` (found by `git blame` on the lines the fix removed or changed; label `introducing-commit`, or `introducing-commit-approx` where the fixed lines were re-edited after the introducing commit), ground truth = file + mechanism regex + one-line description taken from the fix, fix commit and test change recorded. All patches are at most 600 lines (max 192).
- Split (deterministic, `scripts/bench_corpus.py split`): the 26 real cases sorted by sha256(id), first 8 TRAIN, remaining 18 TEST; the held-out fixture is public in this repository, so it is TRAIN by rule. TRAIN = 9 cases, TEST = 18 cases. TEST ground truth is not committed; the repository holds only the manifest (URLs, licences, SHAs) for TEST.
- Reviewers: `claude -p --model sonnet`, read-only tools, user settings excluded, see `change.patch` alone (no history). Perun arms load `.claude/skills/deep-code-review` exported from origin/main at 2f046bf5 (v1.504.0). Prompt asks for a final JSON findings array; scoring reuses `scripts/score_review.py` (matcher_version 1).
- Strict precision = findings matching ground truth / findings. Verified precision = (matched + extras a separate verifier session labels `real` or `gt_same`) / findings; the verifier reads the patch and the pre-fix file, sees the reference bug description, and labels each strict-unmatched finding. Adjudicated recall counts a case when strict hit or the verifier says an extra is the same bug (a matcher miss).

## Results (TEST, 18 cases / 18 bugs)
| Reviewer | Recall strict | Recall adjudicated | Findings | Precision strict | Precision verified | Review cost | Review time | Turns |
|---|---|---|---|---|---|---|---|---|
| Perun single pass (Sonnet + skill) | 0.56 (10/18, 95% CI 0.34-0.75) | 0.56 | 38 | 0.53 | 0.68 | $1.90 ($0.106/case) + $0.85 verify | 298 s (17/case) | 55 |
| Perun + seeded gap pass | 0.72 (13/18, 95% CI 0.49-0.88) | 0.72 | 58 | 0.55 | 0.72 | $4.33 ($0.241/case) + $0.80 verify | 644 s (36/case) | 125 |
| Plain Sonnet (no skill) | 0.61 (11/18, 95% CI 0.39-0.80) | 0.67 | 41 | 0.54 | 0.66 | $1.05 ($0.058/case) + $0.68 verify | 278 s (15/case) | 36 |
| shellcheck (shell) / semgrep p/default (other) | 0.00 (0/18, 95% CI 0.00-0.18) | 0.00 | 15 | 0.00 | 0.00 | $0.00 ($0.000/case) + $0.23 verify | 336 s (19/case) | 0 |

Perun + gap cost and time include the first pass (the gap pass is seeded with the perun arm's findings and adds its own findings to the list, unfiltered). Tool time is wall time of scans, cost is zero.

Verifier verdicts on strict-unmatched findings:

| Arm | real | gt_same | not_a_bug | unverifiable |
|---|---|---|---|---|
| perun | 6 | 0 | 10 | 2 |
| perun-gap | 10 | 0 | 12 | 4 |
| plain | 4 | 1 | 12 | 2 |
| tools | 0 | 0 | 15 | 0 |


## Reading and caveats
- Perun single vs plain: no measurable difference here. On small single-purpose diffs the skill's DIFF quick-path means the reviewer reads SKILL.md and the patch only (about 3 turns); the skill's depth routes are not exercised. This corpus under-tests the multi-file, high-stakes paths the skill targets.
- Gap pass adds recall (it recovered 3 cases the single pass missed) at 2.3x the cost and with 20 more findings, 4 of them confirmed real by the verifier. Directionally consistent with the earlier single-fixture measurement in `method-situational.md`.
- Verified precision depends on a model verifier; its verdicts are recorded per finding in the run outputs. Low-confidence labels are `unverifiable` and still count against precision.
- Introducing-commit diffs restricted to the buggy file(s); a reviewer sees the patch's post-image, which can differ from the pre-fix file the verifier reads when later commits touched other lines.
- Tools arm runs on the whole pre-fix file (not the patch hunk); semgrep ruleset `p/default`, shellcheck default severity. Their findings are style or security-pattern notes that never state a bug mechanism, so recall 0 is expected for mechanism-level logic bugs.
- One run per arm per case; model nondeterminism not averaged. Re-run before drawing conclusions from differences under about 0.2.
- Overfit guard: tune only against TRAIN; report on TEST once per skill release; if TEST is ever used to tune, re-split from new cases.
- Per-case hit/miss and the cases every arm missed are kept out of the repository on purpose: TEST must stay unseen by anyone tuning the skill.

## Reproduce
`python3 scripts/bench_corpus.py run --corpus <private corpus> --arm perun --skill <skill dir exported from main> --out <dir>`, then `--arm perun-gap | plain | tools`, `verify` per arm, and `report`. The private corpus is rebuilt from `manifest.json`: take each case's `intro_sha` diff of the buggy file(s) (`git diff <intro>^ <intro> -- <files>`) and write ground truth from the fix commit `fix_sha`. TRAIN cases are committed in full under `train/`.
