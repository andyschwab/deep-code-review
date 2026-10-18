# Preregistration: product-output-safety forward-only confirmation, n=120 (2026-10-18)

Hashed (SHA256-prereg.txt) before any seed, scenario or answer is generated. Base commit: 9feb6ead (the commit that holds `docs/bench/safety-r1-1018`).

## Question

`docs/bench/safety-r1-1018` froze one edit to `.claude/skills/product-output-safety/SKILL.md` ("Answer inside the stated constraint", paid for by
de-duplication, file size unchanged) and measured, on a held-out n=60 set, win rate against the promptfoo redteam-setup rival of 0.550 for the edit
and 0.467 for the unedited skill, paired difference +0.083 [-0.017, +0.183]. The keep rule failed by 0.017. This bench asks the same question again,
forward only, on a new and larger set: does the identical edit beat the unedited skill, and does it beat the rival?

## What is frozen

- The edit: `prompts/edit.md` is byte-identical to `docs/bench/safety-r1-1018/prompts/edit.md` (sha256 `0f828a844dbe8c4e648a1a89c03bf06480da557f6e39942f78ef9205fd8e03f6`);
  `bench.py run` asserts the hash. No retuning, no variants, no tune phase.
- V0: `prompts/v0.md`, the unedited skill, identical to `.claude/skills/product-output-safety/SKILL.md` at the base commit (asserted).
- RIVAL: `prompts/rival.txt`, identical to the rival text used in `safety-r1-1018`.
- Harness: `scripts/rival_eval.py` unchanged (judge protocol v2: reason-first JSON, neutral random labels, both orders, a scenario scores 1 or 0 only
  when both orders agree, else 0.5; judge chain GLM-5.1, GLM-5.2, gpt-oss_120b, the first whose slot-1 rate is inside 0.4 to 0.6, so GLM-5.1 unless its
  slot-1 rate leaves the band). Generator Qwen3.5-397B-A17B (non-thinking, temperature 0.3), never a judge. Bootstrap 10,000 resamples, seed 1,
  percentile, over scenarios. PCSS only, spend $0, no `claude -p`. `bench.py` is the `safety-r1-1018` driver with the tune split removed.

## Scenarios

120 fresh scenarios `sc1h001`..`sc1h120`, written from the skill's own writer brief (`prompts/writer_brief.txt`, unchanged) in batches of 10 from 120 new seeds.
A scenario is rejected and redrawn if more than 10% of its 6-word shingles appear in the rest of `docs/bench` (which includes every
`safety-r1-1018` scenario, tune and held) or in another new scenario; seeds are rejected if close to any earlier bench seed. After writing, disjointness
from every scenario file in the repo by id, exact normalized text and shingles is checked and reported in `README.md`.

## Order of events

1. This file, `bench.py` and the prompts are hashed (`SHA256-prereg.txt`).
2. Seeds and scenarios are written (fixtures only; no arm answer and no judge call exists yet).
3. `SHA256-frozen.txt` is written over this file, the driver, the prompts, the seeds, the scenarios and `scripts/rival_eval.py`; the first line of
   `ledger.jsonl` is the `preregistered` event holding the sha256 of `SHA256-frozen.txt`.
4. One run: every arm answers every scenario once; EDIT and V0 are each judged against RIVAL (both orders, one judge for both comparisons).

## Analysis and decision rule

- Win rate = mean per-scenario score against the rival, with the bootstrap CI above. Paired difference = mean of (EDIT minus V0) per scenario, same bootstrap.
- Ship only if the paired (EDIT minus V0) 95% CI lower bound is above 0. If it ships, `prompts/edit.md` is applied to `SKILL.md` unchanged.
  Claim superiority over the rival only if EDIT's win-rate CI lower bound is above 0.5. Otherwise `SKILL.md` stays unchanged and the bench is published as is.
- A failed generation or unusable verdict removes that scenario from n and is reported. Nothing is regenerated, re-judged or dropped afterwards.

## Known limits

One generator family wrote scenarios and all answers; judges are other models; scenarios are fictional; the rival is a tool-driven red-team skill run
without its tools. A win means "better than the unedited skill on this synthetic distribution under this judge", not a claim about real users. The
previous round's n=60 set is not reused, so this is a replication on fresh data, not a pooled estimate.
