# Preregistration: fresh replication of three standing wins, n=150 each (2026-10-18)

This file is hashed (SHA256-prereg.txt) before any seed, scenario or answer is generated.

Base: `origin/main` commit `18801f125656756027e8bfaf190b06e15f2c9d16`. All model calls go to the PCSS endpoint ($0, no paid call, no `claude -p`).

## Question and disclosure (second look)

Do the shipped, unedited `agentic-ceo`, `positioning` and `product-discovery` skills still beat their public rivals on a fresh held-out
set 2.5 times the size of the first confirmation? The three rows of `docs/perun-vs-rivals.md` currently read "Win" from one run,
`docs/bench/confirm-v2-1017` (n=60 each: agentic-ceo 0.733 [0.642, 0.825], positioning 0.650 [0.550, 0.742], product-discovery 0.692 [0.592, 0.783]).
This is the second look at each claim, run to replicate it, not to improve it. Earlier looks at product-discovery and positioning (n=10 to 20,
rubric-free judges) did not confirm them or were not run; those results stay recorded in `docs/perun-vs-rivals.md`. The rule below is applied
to this run alone; a pass here is one more look, not the end of the multiplicity, and a fail is published as a fail.

## Fixed design (same method as `../confirm-v2-1017`, only n and ids change)

- Harness: `scripts/rival_eval.py` (hash in SHA256-frozen.txt), unchanged. `confirm.py` in this dir is the confirm-v2-1017 copy with only these
  changes: N 60 to 150, three-digit seed numbers, scenario ids `wNNN`, a rotating industry focus in the seed prompt, and `run` taking one skill
  so the three skills can run as parallel processes. No skill text, rival text, harness code, judge prompt or generator setting is edited after this file.
- Perun arm: each skill's `SKILL.md` at the base commit, byte-identical (hash in SHA256-frozen.txt). `agentic-ceo/SKILL.md` differs from
  the confirm-v2-1017 arm by one later wording-only commit (`ba7b3624`); `positioning` and `product-discovery` are byte-identical to it.
  Rival arm: the same rivals as confirm-v2-1017 (agentic-ceo vs `obra/superpowers` using-superpowers, positioning vs `deanpeters`
  positioning-statement, product-discovery vs the `phuryn` pm-skills selection), recorded by text hash; the fetched hashes were checked
  against confirm-v2-1017's records before this file was written and match.
  Both arms answer every scenario once, no tools.
- Generator: Qwen3.5-397B-A17B (non-thinking, temperature 0.3), never a judge.
- Judge v2, both orders, chain GLM-5.1, then GLM-5.2, then gpt-oss_120b: the first whose slot-1 rate (share of decisive picks in the first
  position) is inside 0.4 to 0.6 scores the skill; all biased means no verdict. A scenario scores 1 or 0 only when both orders agree, else 0.5.
- Scenarios: 150 fresh per skill, ids `w001` to `w150`. Seeds drawn by the generator, rejected when close to any existing `docs/bench` seed
  or to each other. Scenarios written in batches of 6 from each skill's own existing writer brief. Disjointness: no id equals any id in an
  existing bench scenario file; any scenario sharing more than 10% of its 6-word shingles with the `docs/bench` corpus (scenario, seed and
  prompt files, including confirm-v2-1017's sets; outputs and judge records excluded) or with another new scenario is regenerated before
  freezing; `python3 scripts/bench_check.py --changed origin/main` must also pass. The set is frozen by hash (SHA256-frozen.txt) and the
  timestamped `preregistered` line 1 of `ledger.jsonl` records the hash of that file before any answer or verdict is generated.
- Answers and verdicts are generated once and cached; nothing is regenerated, re-judged with another protocol, or dropped after the fact.
  A failed generation or unusable verdict removes the scenario from n and is reported.

## Decision rule (fixed now)

Per skill: win rate = mean of per-scenario scores, 95% CI = percentile bootstrap over scenarios (10,000 resamples, seed 1).
If the CI lower bound is above 0.5 the row keeps "Win". Otherwise the row is downgraded (to "No win shown" with the n=150 numbers beside the
n=60 ones). No verdict (all judges biased, or n under 10) counts as not above 0.5. No multiplicity correction; three tests, reported as three.

## Known limits (stated up front)

One generator family wrote the scenarios and both arms' answers; judges are other models but synthetic and position-biased (hence both
orders and strict agreement). Arms run without tools. A pass supports "beats this rival on this fictional scenario distribution under this
judge", not a claim about real users. Rival text for positioning is CC BY-NC-SA and is fetched at run time, not committed.
