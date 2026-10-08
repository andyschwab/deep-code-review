# Review benchmark: first baseline on the TEST split

Measured on deep-code-review skill v1.504.0 (origin/main 2f046bf5), model `sonnet` via `claude -p`, 2026-10-07. Re-measure on any later skill version before comparing.

BLUF: on 18 held-out real bug-fix cases, no configuration finds more than about a third of the bugs. Perun single pass, Perun + seeded gap pass and plain Sonnet are indistinguishable on recall (strict 0.33 / 0.33 / 0.33; verifier-adjudicated 0.28 / 0.28 / 0.22). Perun's findings are more often real (verified precision 0.53 vs 0.39 plain), at 1.9x the review cost. The gap pass added 21 findings and no recall here, at 2.2x cost. Static tools found none. n = 18 bugs, one run per arm: every difference is inside the confidence interval.

## Setup
- Corpus: 26 real bug-fix cases from permissive-licence public repositories (MIT, BSD-3-Clause, Apache-2.0; shell 6, Python 7, JS 6, Go 7) plus the 6-bug held-out fixture from PR #1354 (27 cases). Each case: the introducing commit's diff of the buggy file(s) as `change.patch` (found by `git blame` on the lines the fix removed or changed; label `introducing-commit`, or `introducing-commit-approx` where the fixed lines were re-edited after the introducing commit), ground truth = file + mechanism regex + one-line description taken from the fix. Every patch is at most 600 lines (max 192).
- Split (deterministic, `scripts/bench_corpus.py split`): the 26 real cases sorted by sha256(id), first 8 TRAIN, remaining 18 TEST; the held-out fixture is public in this repository, so it is TRAIN by rule. TRAIN = 9, TEST = 18. TEST ground truth, patches and fix/introducing SHAs are not committed; the committed manifest gives TEST entries hashed ids, language, repository URL and licence only.
- Reviewers: `claude -p --model sonnet`, read-only tools, user settings excluded, working directory with an opaque name, see `change.patch` alone (no history). Perun arms load `.claude/skills/deep-code-review` exported from origin/main at 2f046bf5. Prompt asks for a final JSON findings array; scoring reuses `scripts/score_review.py` (matcher_version 2).
- Strict = regex matcher from `score_review.py` (file basename and mechanism regex). Adjudicated recall = a separate verifier session, blind to the regex, labelled some finding `gt_same` (same root cause as the reference bug). Verified precision = findings labelled `real` or `gt_same` / findings. The verifier reads the patch and the pre-fix file and sees the reference bug description. Cases whose run or verifier failed are excluded from every denominator and shown in the `Errors` column (0 here).

## Results (TEST, 18 cases / 18 bugs)
| Reviewer | Recall strict | Recall adjudicated | Findings | Precision strict | Precision verified | Review cost | Review time | Errors |
|---|---|---|---|---|---|---|---|---|
| Perun single pass (Sonnet + skill) | 0.33 (6/18, CI 0.16-0.56) | 0.28 (5/18, CI 0.12-0.51) | 36 | 0.22 | 0.53 | $1.84 ($0.102/case) + $0.90 verify | 273 s (15/case) | 0 |
| Perun + seeded gap pass | 0.33 (6/18, CI 0.16-0.56) | 0.28 (5/18, CI 0.12-0.51) | 57 | 0.17 | 0.56 | $3.98 ($0.221/case) + $0.97 verify | 577 s (32/case) | 0 |
| Plain Sonnet (no skill) | 0.33 (6/18, CI 0.16-0.56) | 0.22 (4/18, CI 0.09-0.45) | 39 | 0.18 | 0.39 | $0.99 ($0.055/case) + $0.84 verify | 250 s (14/case) | 0 |
| shellcheck (shell) / semgrep p/default (other) | 0.00 (0/18, CI 0.00-0.18) | 0.00 (0/18, CI 0.00-0.18) | 15 | 0.00 | 0.00 | $0.00 ($0.000/case) + $0.29 verify | 200 s (11/case) | 0 |

Perun + gap cost and time include the first pass: the gap pass is seeded with the perun arm's findings and its new findings are appended unfiltered. Tool time is wall time of scans, cost is zero. Strict precision is low for every arm because the matcher only credits the one reference bug per case; verified precision is the meaningful number.

Verifier verdicts on all findings:

| Arm | gt_same | real | not_a_bug | unverifiable |
|---|---|---|---|---|
| perun | 5 | 14 | 13 | 4 |
| perun-gap | 5 | 27 | 19 | 6 |
| plain | 4 | 11 | 19 | 5 |
| tools | 0 | 0 | 15 | 0 |


## Reading and caveats
- On small single-purpose diffs the skill's DIFF quick-path means the Perun reviewer reads SKILL.md and the patch only (about 3 turns); the depth routes are not exercised. This corpus under-tests the multi-file, high-stakes paths the skill targets.
- Run-to-run noise is large. A first full run (before the matcher fixes below, with the case id visible in the reviewer's working-directory name) scored Perun single 0.56, gap 0.72, plain 0.61 on the loose matchers and was discarded. Its apparent gap-pass gain did not reproduce here; treat any single-run gap-pass or skill delta as unproven until repeated.
- The matcher was too loose in that first run: many of its "hits" were unrelated findings that happened to contain a keyword (for example an ordering finding credited to an unrelated ordering bug). All matchers were tightened to mechanism phrases (matcher_version 2) and every finding is now also judged by the blind verifier; strict and adjudicated recall now agree to within 2 cases. The verifier is a model: its verdicts are stored per finding, and `unverifiable` still counts against precision.
- Introducing-commit diffs are restricted to the buggy file(s); a reviewer sees the patch's post-image, which can differ from the pre-fix file the verifier reads when later commits touched other lines.
- Tools arm runs on the whole pre-fix file (not the patch hunk); semgrep ruleset `p/default`, shellcheck default severity. Their findings are style or security-pattern notes, not bug mechanisms, so recall 0 is expected for logic bugs.
- Overfit guard: tune only against TRAIN; report on TEST once per skill release; if TEST is ever used to tune, re-split from new cases.
- Raw outputs and verdicts: work dir `out/` (not committed).
- Per-case hit/miss and the cases every arm missed are kept out of the repository on purpose: TEST must stay unseen by anyone tuning the skill.

## Reproduce
`python3 scripts/bench_corpus.py run --corpus <private corpus> --arm perun --skill <skill dir exported from main> --out <dir>`, then `--arm perun-gap | plain | tools`, `verify` per arm, and `report`. `public-manifest` writes the committable manifest from the private one. The private corpus is rebuilt by taking each case's introducing commit diff of the buggy file(s) (`git diff <intro>^ <intro> -- <files>`) and writing ground truth from the fix commit. TRAIN cases are committed in full under `train/`; upstream licences are in `NOTICE`.
