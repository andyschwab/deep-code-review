# Review benchmark results

## 2026-10-14: against popular review skills, plus three cost and precision variants (current)

Same harness as the 2026-10-12 run below (Sonnet `claude-sonnet-5-5`, strict MCP, repo access with Read, Grep and Glob, change applied at HEAD), 37 of its 39 cases (two cases' repositories could not be rebuilt), one run per case. Every rule was written down before the run. "Precision" is the share of findings the verifier judged real. "Strict recall" matches findings against the known bug with no model in the loop.

| Reviewer | Recall (adjudicated) | Strict recall | Precision | F1 | Review cost |
|---|---|---|---|---|---|
| Plain "review this diff" prompt | 0.297 | 0.351 | 0.728 | 0.422 | $0.098 |
| Perun (v1.573.0) | 0.297 | 0.324 | 0.862 | 0.442 | $0.136 |
| obra/superpowers requesting-code-review | 0.297 | 0.405 | 0.775 | 0.430 | $0.096 |
| Anthropic pr-review-toolkit code-reviewer | 0.297 | 0.324 | 0.933 | 0.451 | $0.090 |
| wshobson/agents code-reviewer | 0.297 | 0.405 | 0.724 | 0.422 | $0.097 |

- **Bug finding is a tie.** Every F1 difference between Perun and the others has a 95% interval that includes 0. All five reviewers caught the bug in 11 of 37 cases; which cases differed by reviewer.
- **Precision:** Perun is above the plain prompt and wshobson (intervals exclude 0) and below the Anthropic toolkit (not distinguishable).
- **Cost:** a Perun review costs about 1.5 times the toolkit's and about 1.4 times the others'. About two-thirds of the gap is the larger cached prompt prefix (SKILL.md); the rest is longer output.

Variants tried the same day, none shipped:

| Variant | Result | Why it was not shipped |
|---|---|---|
| `references/compact-mode.md` alone as the instructions (2 KB instead of SKILL.md) | precision 0.567, recall 0.324, $0.177 per case with verifier | Precision fell 0.295 below full Perun (interval -0.413 to -0.184) and 0.162 below the plain prompt. The full SKILL.md is what buys precision. |
| SKILL.md cut to 11 KB, full-repo material moved to a reference | precision 0.880, recall 0.324, review $0.130 | Only 4% cheaper (bar was 20%), and the precision interval (-0.077 to +0.113) was too wide to show it did not get worse. |
| An extra pass that only removes findings it cannot confirm | precision 0.97 on paper | The pass and the grader are the same model, so it mostly pre-applies the grader. Judge-free strict recall fell from 0.324 to 0.270. |

A follow-up on 21 cases never used before, judged by `claude-opus-5-5` (a different model from the reviewers), also tied the toolkit on precision: Perun plus the remove-only pass 0.881, toolkit 0.886, difference -0.005 (interval -0.106 to +0.085). On those cases Perun alone matched more known bugs than the toolkit (0.429 against 0.238; exploratory, not a pre-registered claim). Pooled with the 37 cases above (58 in all), that gap is +0.069 with an interval of -0.017 to +0.172: a tie. Perun also reports about 50% more findings, which raises strict matches by itself.

**Reading.** Measured on bug finding alone, Perun ties the best popular review prompt and costs more. Its measured edges are fewer false alarms than a plain prompt, plus the delivery tooling and gates the other review prompts do not ship. Do not re-run the three variants above expecting a different answer; a new idea needs fresh cases and a judge from a different model.

## 2026-10-12: paired run, strict MCP (previous)

BLUF: on 39 held-out real bug fixes Perun (one pass) beat a plain prompt on recall by +0.103 (verifier-judged, interval 0.000 to +0.231), a borderline result. Against `/code-review` it matched recall (+0.000) with verified precision +0.502 and F1 +0.238 (n = 34). Model `claude-sonnet-5-5`, `--strict-mcp-config` on every call, same day, same cases, same verifier. Recall adjudicated = verifier-judged; recall strict = fixed text match; verified precision = findings the verifier confirmed real; F1 = harmonic mean of adjudicated recall and verified precision. Intervals: paired bootstrap, 10000 case resamples, seed 1.

The `/code-review` arms ran at the pre-fix commit with the change staged; its native JSON was mapped to file, line and text. The verified arm keeps only findings whose failure path a verifier call confirmed in code. 5 of 39 cases did not finish before the spend cap and are excluded from the 34-case comparison.

Perun against a plain prompt (39 cases, paired):

| | Plain prompt | Perun, one pass | Perun minus plain [95% interval] |
|---|---|---|---|
| Recall, verifier-judged | 0.385 | 0.487 | +0.103 [0.000, +0.231] |
| Recall, strict | 0.462 | 0.615 | +0.154 [0.000, +0.308] |
| Verified precision | 0.778 | 0.800 | +0.022 [-0.104, +0.142] |
| F1 | 0.515 | 0.606 | not computed |
| Cost per case | $0.06 | $0.12 | about 2 times |

Perun against `/code-review` (34 of the 39 cases; 5 did not finish before the spend cap):

| | Plain prompt | Perun | `/code-review` | `/code-review` plus verifier |
|---|---|---|---|---|
| Recall, verifier-judged | 0.382 | 0.529 | 0.529 | 0.412 |
| Recall, strict | 0.441 | 0.647 | 0.735 | 0.529 |
| Verified precision | 0.792 | 0.839 | 0.336 | 0.688 |
| F1 | 0.516 | 0.649 | 0.411 | 0.515 |
| Cost per case | $0.061 | $0.126 | $0.109 | $0.192 |

Paired differences, Perun minus the other (95% interval):

| Against | Recall, verifier-judged | Verified precision | F1 |
|---|---|---|---|
| `/code-review` | +0.000 [-0.088, +0.088] | +0.502 [+0.405, +0.590] | +0.238 [+0.135, +0.333] |
| `/code-review` plus verifier | +0.118 [+0.029, +0.235] | +0.151 [+0.004, +0.292] | +0.134 [+0.043, +0.240] |

Strict recall against `/code-review` was -0.088 [-0.206, +0.029]: `/code-review` caught as
many or slightly more by the strict match, with about 3 times as many findings.

Caveats: one model; one 39-case corpus (34 for `/code-review`); one run per case; the verifier is an LLM, not a person; recall against plain is borderline (interval lower bound 0). Raw tables (`bench90-strict.md`, `bench90-strict-cr.md`) are not committed.

## Earlier baseline (2026-10-07, superseded; 18 cases, different setup)

Measured on deep-code-review skill v1.504.0 (origin/main 2f046bf5), model `sonnet` via `claude -p`, 2026-10-07. Re-measure on any later skill version before comparing.

BLUF: on 18 held-out real bug-fix cases, no configuration finds more than about a third of the bugs. Perun single pass, Perun + seeded gap pass and plain Sonnet are indistinguishable on recall (strict 0.33 / 0.33 / 0.33; verifier-adjudicated 0.28 / 0.28 / 0.22). Perun's findings are more often real (verified precision 0.53 vs 0.39 plain), at 1.9x the review cost. The gap pass added 21 findings and no recall here, at 2.2x cost. Static tools found none. n = 18 bugs, one run per arm: every difference is inside the confidence interval.

### Setup
- Corpus: 26 real bug-fix cases from permissive-licence public repositories (MIT, BSD-3-Clause, Apache-2.0; shell 6, Python 7, JS 6, Go 7) plus the 6-bug held-out fixture from PR #1354 (27 cases). Each case: the introducing commit's diff of the buggy file(s) as `change.patch` (found by `git blame` on the lines the fix removed or changed; label `introducing-commit`, or `introducing-commit-approx` where the fixed lines were re-edited after the introducing commit), ground truth = file + mechanism regex + one-line description taken from the fix. Every patch is at most 600 lines (max 192).
- Split (deterministic, `scripts/bench_corpus.py split`): the 26 real cases sorted by sha256(id), first 8 TRAIN, remaining 18 TEST; the held-out fixture is public in this repository, so it is TRAIN by rule. TRAIN = 9, TEST = 18. TEST ground truth, patches and fix/introducing SHAs are not committed; the committed manifest gives TEST entries hashed ids, language, repository URL and licence only.
- Reviewers: `claude -p --model sonnet`, read-only tools, user settings excluded, working directory with an opaque name, see `change.patch` alone (no history). Perun arms load `.claude/skills/deep-code-review` exported from origin/main at 2f046bf5. Prompt asks for a final JSON findings array; scoring reuses `scripts/score_review.py` (matcher_version 2).
- Strict = regex matcher from `score_review.py` (file basename and mechanism regex). Adjudicated recall = a separate verifier session, blind to the regex, labelled some finding `gt_same` (same root cause as the reference bug). Verified precision = findings labelled `real` or `gt_same` / findings. The verifier reads the patch and the pre-fix file and sees the reference bug description. Cases whose run or verifier failed are excluded from every denominator and shown in the `Errors` column (0 here).

### Results (TEST, 18 cases / 18 bugs)
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


### Reading and caveats
- On small single-purpose diffs the skill's DIFF quick-path means the Perun reviewer reads SKILL.md and the patch only (about 3 turns); the depth routes are not exercised. This corpus under-tests the multi-file, high-stakes paths the skill targets.
- Run-to-run noise is large. A first full run (before the matcher fixes below, with the case id visible in the reviewer's working-directory name) scored Perun single 0.56, gap 0.72, plain 0.61 on the loose matchers and was discarded. Its apparent gap-pass gain did not reproduce here; treat any single-run gap-pass or skill delta as unproven until repeated.
- The matcher was too loose in that first run: many of its "hits" were unrelated findings that happened to contain a keyword (for example an ordering finding credited to an unrelated ordering bug). All matchers were tightened to mechanism phrases (matcher_version 2) and every finding is now also judged by the blind verifier; strict and adjudicated recall now agree to within 2 cases. The verifier is a model: its verdicts are stored per finding, and `unverifiable` still counts against precision.
- Introducing-commit diffs are restricted to the buggy file(s); a reviewer sees the patch's post-image, which can differ from the pre-fix file the verifier reads when later commits touched other lines.
- Tools arm runs on the whole pre-fix file (not the patch hunk); semgrep ruleset `p/default`, shellcheck default severity. Their findings are style or security-pattern notes, not bug mechanisms, so recall 0 is expected for logic bugs.
- Overfit guard: tune only against TRAIN; report on TEST once per skill release; if TEST is ever used to tune, re-split from new cases.
- Raw outputs and verdicts: work dir `out/` (not committed).
- Per-case hit/miss and the cases every arm missed are kept out of the repository on purpose: TEST must stay unseen by anyone tuning the skill.

### Reproduce
`python3 scripts/bench_corpus.py run --corpus <private corpus> --arm perun --skill <skill dir exported from main> --out <dir>`, then `--arm perun-gap | plain | tools`, `verify` per arm, and `report`. `public-manifest` writes the committable manifest from the private one. The private corpus is rebuilt by taking each case's introducing commit diff of the buggy file(s) (`git diff <intro>^ <intro> -- <files>`) and writing ground truth from the fix commit. TRAIN cases are committed in full under `train/`; upstream licences are in `NOTICE`.
