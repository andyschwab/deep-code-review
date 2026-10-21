# Over-claim bench R4: a claim-first rule (2026-10-21, preregistered, free PCSS models, no paid call): REVERT

BLUF: a 56-word claim-first rule (name the one output that would prove the claim as worded, then look for it; a verified neighbour never upgrades a claim) did not get Perun to or below superpowers on the R3 corpus. Skill text unchanged. The R3 corpus was reused after its labels shaped the rule, so it is no longer held out for this rule (a KEEP would have needed a fresh-corpus replication first). Hypothesis, rule and keep rule are in [`PREREGISTERED.md`](PREREGISTERED.md), frozen by hash before any call (`SHA256-frozen.txt`, first line of `ledger.jsonl`).

## Result (primary model Mistral-Small-3.2:24b, 56 cases, 107 items, one run per arm, temperature 0, fresh generations, bootstrap seed 2)

| Arm | Over-claim (95% interval) | Under-claim (95% interval) |
|---|---|---|
| Perun without the rule (`perun_old`) | 16.8% (10.6 to 23.4) | 12.1% (6.6 to 18.1) |
| Perun with the rule (`perun_new`) | 15.9% (9.8 to 22.2) | 11.2% (5.7 to 16.8) |
| obra/superpowers | 13.1% (7.5 to 19.2) | 7.5% (2.8 to 12.5) |

- Perun-new minus superpowers, over-claim: +2.8 points (-0.9 to +7.3). Keep rule needed this at or below 0: fails.
- Perun-new minus Perun-old, over-claim: -0.9 points (-3.9 to +1.9). Needed below 0: met on the point estimate only; one item.
- Under-claim guardrail (at most 5 points above both): held (+3.7 over superpowers, -0.9 against old).
- Verdict REVERT. Neither contrast is significant, so this is also not a significant loss.
- Stale-evidence items over-claimed: 7 in every arm, including superpowers (7 of the 14 to 18 over-claims). The rule did nothing there, again.
- Where the rule moved things: partial-fix over-claims 4 to 2, hidden-failure 2 to 2 (superpowers 0), skipped-gate 2 to 3 (superpowers 1). Hidden failure and skipped gate are where Perun still trails superpowers.

Qwen3.5-397B-A17B (direction only, cannot change the verdict): old 8.4% over, new 6.5%, superpowers 5.6%; new minus superpowers +0.9 (-3.8 to +5.6). Same ordering, same REVERT by the point rule.

## Caveats
- The R3 corpus was no longer held out: the hypothesis came from R3 per-case labels and case text (no R3 generation text, none was kept). A KEEP would have needed a fresh-corpus replication; the REVERT does not.
- Gold labels were written by the Perun side. One run per arm. The two arms with unchanged prompts landed on the same totals as in R3 (`perun_old` 18 of 107 items, superpowers 14 of 107); item-level agreement was not checked.
- The point-estimate keep rule has no noise margin: one item is 0.9 points. It was preregistered by the requester and kept.
- No `none` arm was run in R4.
- Freeze order is self-attested: the ledger timestamp plus `scripts/bench_check.py` are the only evidence the hashes were written before the first call. Git history does not prove it, because the frozen files, the ledger and the results ship in one commit.
- `per-case-labels.json` holds case id and label only (no generated text). It was produced by `python3 scripts/overclaim_r4_labels.py`, which scores the generations cached by the R4 run (`.bench-cache/overclaim`, not committed), is deterministic (same cache, same bytes) and raises on a cache miss instead of calling a model. The test `scripts/test_overclaim_bench_r4.py` recomputes every rate, interval (bootstrap seed 2) and contrast in both results files from it, locally and offline.

## Reproduce
```
PCSS_ENV_FILE=<path to .env holding PCSS_KEY> python3 scripts/overclaim_bench_r4.py --model Mistral-Small-3.2:24b --write
python3 scripts/test_overclaim_bench_r4.py
python3 scripts/bench_check.py docs/bench/overclaim-r4-1021
```
Key is read from the environment or file and never printed; the superpowers text is fetched from a pinned commit and checked against its file hash (fails closed). `cases.txt` and `perun-old-arm.txt` are byte-identical copies of the R3 files (the tests check this).
