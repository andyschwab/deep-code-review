# Contribution skill, round 4: one edit against the rival, held-out n = 150, 2026-10-18

BLUF: DO NOT SHIP, no win. The frozen edit (v1) scores 0.457 [0.390, 0.523] against github-contributor (48 wins, 41 ties or splits, 61 losses); the shipped text (v0) scores 0.470 [0.403, 0.537] (49 / 43 / 58). Paired difference (v1 minus v0) -0.013, 95% bootstrap CI [-0.083, +0.057] (150 of 150 scored, judge GLM-5.1, slot-1 rate 0.492, healthy). The preregistered keep rule (paired lower bound above 0) fails and v1's win-rate lower bound is below 0.5, so `SKILL.md` is unchanged and no superiority over the rival is claimed. Spend $0.00 (PCSS only).

- Rule, arms, seeds: `PREREGISTERED.md`; hash lists `SHA256-prereg.txt` (before any held-out seed existed) and `SHA256-frozen.txt` (adds the held-out seeds and scenarios, and the final harness); `ledger.jsonl` records the hash of `SHA256-frozen.txt` before any answer or judge call, then the results hash. Tune runs are in `ledger-tune.jsonl`.
- Tune (n = 30, `scenarios-tune.json`, GLM-5.1 only): v0 0.417, F1 0.300, H1 0.508, H2 0.433, H1b 0.383, where H1 and H1b are the same edit up to one pointer sentence, so the tune set was noise. The edit was chosen from a hand reading of the 14 tune scenarios v0 lost in both orders, not from a tune win.
- Held-out: `scenarios-held.json` (r4h01 to r4h150, seeds in `prompts/seeds-held.txt`): at most 0.098 of any scenario's 6-word shingles appear in any text file under `docs/bench` on origin/main at bd8ea910 (re-fetched before the draw and before the freeze), and no id appears there. Raw outputs and verdicts: `results-held/`. Reproduce: `python3 docs/bench/contribution-r4-1018/bench.py run held <out>` then `fold held <out>` (PCSS key from `.env`).

| Judge | Slot-1 | v0 | v1 | Paired diff [95% CI] |
|---|---|---|---|---|
| GLM-5.1 (used, preregistered) | 0.492 | 0.470 | 0.457 | -0.013 [-0.083, +0.057] |
| GLM-5.2 (sensitivity) | 0.535 | 0.487 | 0.410 | -0.077 [-0.150, -0.003] |
| gpt-oss_120b (sensitivity, outside the 0.4 to 0.6 gate) | 0.668 | 0.503 | 0.487 | -0.017 [-0.083, +0.053] |

## Reading

The edit did not help and the second healthy judge scores it lower (the paired lower bound is below zero on all three judges and the upper bound is below zero on GLM-5.2). The shipped text has now scored below 0.5 at the lower bound on three fresh sets (0.558 [0.458, 0.658] at n = 60, 0.522 [0.439, 0.606] at n = 90, 0.470 [0.403, 0.537] at n = 150, all GLM-5.1 against the same rival), and the point estimate drifts down as n grows, so the earlier 0.558 was probably a lucky draw. Across rounds 3 and 4 two prose edits aimed at the loss analyses (answer shape; removing off-topic repo-internal text from the system prompt) both failed to move the rate, and a third (tune only: deliver the artifact and never refuse) looked worse. The rival's lead is on project-specific concreteness (runnable test or generator code, benchmark scripts, batch sizes), which a short prose edit has not reproduced.

## Caveats

Qwen3.5-397B-A17B generates every arm and the scenarios; judges are PCSS models; the rival is one public skill run without its reference files; the seed lines and scenarios come from one writer model; one run per arm. v0 and v1 were each judged against one shared set of rival answers. The harness was changed while drawing the held-out set, before any answer or judge call (see `PREREGISTERED.md`). One output (`results-held/outputs/v0/r4h44-*`) contained a fictional home-directory example path, redacted to `<home>/` here; the judge verdicts were computed on the unredacted text.

## Repro note (2026-10-23)

`scripts/eval-fixtures/rival/contribution/rival.json` reads the live `.claude/skills/contribution/SKILL.md`, which the slim-fast-path change shortened from 7495 to 5356 bytes and whose old body now lives in `references/full-map.md`. The text this bench scored as v0 is the pre-slim file: sha256 `7b7b86bc9a1ab9e7a91f879dfca0369d87a935aff1b4253ec2207096d2d383d3`, equal to `frozen/contribution.v0.md`, at parent commit `0cd954a38476b4d31efc90fd25efb858dfd2c077` (`git show 0cd954a38476b4d31efc90fd25efb858dfd2c077:.claude/skills/contribution/SKILL.md`). To rerun a live-fixture arm against the scored text, use that file, not the working tree. No frozen file here was edited.
