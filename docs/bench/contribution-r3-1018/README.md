# Contribution skill, round 3: one Answer shape edit against the rival, held-out n = 90, 2026-10-18

BLUF: DO NOT SHIP. The frozen edit scores 0.472 [0.383, 0.567] against github-contributor; the current text (v0) scores 0.522 [0.439, 0.606]. Paired difference (edit minus v0) -0.050, 95% bootstrap CI [-0.156, +0.056] (90 of 90 scored, judge GLM-5.1, slot-1 rate 0.483, healthy). The preregistered keep rule (paired lower bound above 0) fails and neither arm's win-rate lower bound is above 0.5, so `SKILL.md` is unchanged and no superiority over the rival is claimed. Spend $0.00 (PCSS only).

- Rule, arms, seeds: `PREREGISTERED.md`; hash list `SHA256-frozen.txt`; `ledger.jsonl` records the preregistration hash before any held-out seed or scenario existed, then the scenario-set hash and the results hash. Tune runs are in `ledger-tune.jsonl`.
- Tune (n = 30, `scenarios-tune.json`, GLM-5.1 only): four variants (`prompts/variants/E1.md` to `E4.md`), paired differences 0.000, +0.033, +0.017, +0.017, none separable from zero. E4 was frozen on the loss diagnosis, not on a tune win.
- Held-out: `scenarios-held.json` (r3h01 to r3h90, seeds in `prompts/seeds-held.txt`, written after the freeze); maximum 6-word-shingle overlap with every earlier contribution set and the tune set 0.029. Raw outputs and verdicts: `results-held/`. Reproduce: `python3 docs/bench/contribution-r3-1018/bench.py run held <out>` then `fold held <out>` (PCSS key from `.env`).

| Judge | Slot-1 | v0 | edit | Paired diff [95% CI] |
|---|---|---|---|---|
| GLM-5.1 (used, preregistered) | 0.483 | 0.522 | 0.472 | -0.050 [-0.156, +0.056] |
| GLM-5.2 (sensitivity) | 0.534 | 0.417 | 0.517 | +0.100 [+0.006, +0.194] |
| gpt-oss_120b (sensitivity, outside the 0.4 to 0.6 gate) | 0.641 | 0.467 | 0.417 | -0.050 [-0.156, +0.056] |

Strict result for the edit under the used judge: 34 wins, 17 ties or splits, 39 losses. The judges disagree on the sign, so the edit's effect is unresolved at this n; the rule names GLM-5.1, which is negative.

## Reading

Round 2's 0.558 for the shipped text was not reproduced on a fresh, larger set: the same text (v0 here) scored 0.522 [0.439, 0.606] under the same judge, so the shipped text's lower bound stays below 0.5 and the gap to the rival is not closed. Rewriting the Answer shape paragraph toward concrete, runnable, decisive answers did not help under the preregistered judge.

## Caveats

Qwen3.5-397B-A17B generates every arm (not necessarily the model the skill runs on); judges are PCSS models; the rival is one public skill; the seed lines and scenarios are drafted by one writer model; one run per arm. v0 and the edit were each judged against one shared set of rival answers. One generated output (`results-held/outputs/v1/r3h08-*`) contained a home-directory example path, which is redacted to `<home>/` here; the judge verdicts were computed on the unredacted text. Likewise one output (`results-held/outputs/v1/r3h73-*`) contained a 32-plus-character fictional `client_secret` placeholder that matches the repository's secret-pattern gate; its value is replaced with `REDACTED_PLACEHOLDER`, and the verdicts were computed on the original text.
