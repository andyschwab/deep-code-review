# Delivery-plan bench, shipped skill vs Superpowers, n=150, 2026-10-18

Question: does the shipped, unedited `agentic-delivery/SKILL.md` (version 1.593.0, `prompts/ship.txt`) beat Superpowers on 150 fresh held-out tickets? Preregistered in `PREREGISTERED.md` (hashes in `SHA256-frozen.txt`, first `ledger.jsonl` line `preregistered`, then `seeds_frozen`, `amended` and `tickets_frozen` before any plan existed). PCSS models only, 0 paid calls, judge prompt v2 from `scripts/rival_eval.py`, three judges, both orders, strict agreement, then majority, bootstrap 10000 with seed 1, the same code as `../delivery-r2-1017`.

Result (n=150 tickets `sup-001`..`sup-150`, win rate against Superpowers, 95% bootstrap CI):

| Arm | Win rate [95% CI] | W / L / mixed | DeepSeek-V4-Flash | GLM-5.2 | gpt-oss_120b | Slot-1 rate (ds, glm, j3) |
|---|---|---|---|---|---|---|
| ship (shipped skill) | 0.550 [0.507, 0.593] | 31 / 16 / 103 | 0.572 | 0.513 | 0.563 | 0.65, 0.83, 0.82 |

Decision: the preregistered rule (superiority iff the CI lower bound is above 0.5) passes, 0.507 against 0.5. Superiority over Superpowers on this synthetic distribution under this panel is therefore claimed, with these limits stated rather than hidden:

- The margin is 0.007. The interval is a percentile bootstrap over 150 tickets; a different draw of tickets or judge sampling could land either side.
- Multiplicity: this is the fourth look at one claim (see `PREREGISTERED.md`). Earlier non-wins were n=40 at 0.562 [0.487, 0.637] and n=60 at 0.517 [0.450, 0.583]. No adjustment was applied.
- 103 of 150 tickets are 0.5 because the three judges are position-biased (slot-1 rates 0.65 to 0.83) and strict two-order agreement discards disagreements; the effect is 31 wins against 16 losses on the 47 decided tickets. Per judge, GLM-5.2 alone has a lower bound (0.470) below 0.5.
- One generator family writes tickets and both arms' plans, arms run without tools, and the judges are LLMs. This is not evidence about real users.

Deviations, all before any plan or judge record: (1) the seeds step ran three times (a first run was denied network access and wrote nothing, a second passed 144 of 150 archetypes and was discarded, a third passed 150 and was frozen). (2) The frozen tickets step aborted with 9 tickets still above the 0.10 shingle gate after 6 redraws and wrote nothing; `AMENDMENT-1.md` raised the redraw cap to 30 (`SHA256-amended.txt`, `amended` ledger event), after which the step produced 150 tickets, maximum shingle share 0.10 at accept time. The aborted run's draws were discarded. Because `bench.py` was edited after the preregistered hash, the committed `bench.py` hash differs from its `SHA256-frozen.txt` line by design; `SHA256-amended.txt` carries the current one. Failed network calls (10 `error` lines in `ledger.jsonl`) wrote nothing and were re-run.

Files: `bench.py`, `run.sh`, `prompts/` (seed brief, seeds, ship), `tickets.json`, `outputs/<arm>/<ticket>.txt`, `judge/<judge>/ship__sp/<order>/<ticket>.json`, `results/ship__sp.json`, `ledger.jsonl`. Re-score with `python3 -I bench.py score ship sp`; re-running generation needs `PCSS_KEY` in the environment.
