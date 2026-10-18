# Preregistration: contribution skill, round 3 (2026-10-18)

Hashed (`SHA256-frozen.txt`, hash in `ledger.jsonl`) before any held-out seed, scenario, answer or judge call exists. Every model call goes to the PCSS endpoint ($0); no `claude -p`. Base: origin/main at eb3c04b3.

## Question

Round 2 (`docs/bench/contrib-narrow-r2-1018`) kept the narrowed skill on the paired rule but did not beat the rival: 0.558 [0.458, 0.658] against github-contributor. This round freezes one edit to the Answer shape paragraph of `.claude/skills/contribution/SKILL.md` and asks two questions on a fresh held-out set: does the edit beat the current text (v0), and does it beat the rival?

## Arms

- v0: `frozen/contribution.v0.md`, byte-identical to `.claude/skills/contribution/SKILL.md` at the base (7495 bytes).
- v1: `frozen/contribution.v1.md` (= `prompts/variants/E4.md`), v0 with the Answer shape paragraph rewritten (produce the requested artifact in full, weight on runnable code and exact commands, recommend one course and say why, steps and provenance only when needed) and the Verification list of eval ids shortened to one line (it duplicates `evals/evals.json`), which pays for the longer paragraph: 7429 bytes, under the 7531-byte budget. If the keep rule passes, `SKILL.md` becomes byte-identical to v1.
- Rival: `frozen/rival.md` (daymade github-contributor, MIT, sha256 prefix 98e03b82), byte-identical to round 2's.

## Tune phase (finished, logged in `ledger-tune.jsonl`)

30 scenarios (`scenarios-tune.json`, ids r3t01 to r3t30, seeds drafted by the blind writer into `prompts/seeds-tune.txt`), judge GLM-5.1 only, four variants E1 to E4 (`prompts/variants/`). Paired differences were 0.000, +0.033, +0.017 and +0.017, none distinguishable from zero at n = 30 (E2's run also resampled v0). E4 is frozen because it follows the loss diagnosis (the rival wins on decisive, concrete, ready-to-use answers; the skill's own answers were process-heavy), not because it won the tune set. The tune split never produces a verdict.

## Held-out set

n = 90 scenarios, ids r3h01 to r3h90, written after this file is frozen: 90 new seeds drafted by the blind writer (Qwen3.5-397B-A17B, temperature 0.9, told to avoid every round-2 seed) into `prompts/seeds-held.txt`, scenarios from `prompts/brief.txt` in batches of 10 (temperature 0.7, no skill text shown). Disjointness: ids differ from every earlier set by prefix; `bench.py write` fails closed if any scenario shares more than 0.3 of its 6-word shingles with the round-2 held-out set, the two 2026-10-17 contribution sets or this round's tune set.

## Run and decision rule

Generator for all arms: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, the harness's GEN_TASK wrapper; the rival's answer is generated once per scenario and shared by both arms. Judge: the v2 protocol in `scripts/rival_eval.py` (random three-letter labels, short analysis before the verdict, both orders); the first of GLM-5.1, GLM-5.2, gpt-oss_120b whose pooled slot-1 rate lies in 0.4 to 0.6 scores both arms (GLM-5.1 unless it leaves the band); others are sensitivity only; the generator is never a judge. A scenario scores 1 when the arm wins in both orders, 0 when it loses in both, else 0.5. Bootstrap: 10,000 resamples over scenarios, percentile, seed 1.

- KEEP (edit `SKILL.md`) only if at least 81 of 90 scenarios are scored by a healthy judge and the paired difference (v1 minus v0) has a lower 95% bound above 0. Otherwise only this record ships.
- Superiority over the rival is claimed only if v1's win-rate lower bound is above 0.5.
- One run per arm; no re-runs, no judge swapping, no scenario edits after a result is seen. Records are never overwritten.
