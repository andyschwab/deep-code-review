# Delivery-plan bench, round 2, 2026-10-17

Question: on fresh tickets with no id collisions, does the round-1 `agentic-delivery/SKILL.md` edit (the "Plan answers" paragraph plus about 370 bytes of tightened wording) beat the unedited skill, and does either beat Superpowers? Preregistered in `PREREGISTERED.md` (hashes in `SHA256-frozen.txt`, timestamped `preregistered` line in `ledger.jsonl`, `tickets_frozen` line before any plan was generated). PCSS models only, 0 paid calls, judge prompt v2 from `scripts/rival_eval.py`, three judges, both orders, strict agreement, then majority.

Result (n=40 tickets `h2-01`..`h2-40`, win rate against Superpowers, 95% bootstrap CI):

| Arm | Win rate [95% CI] | W / L / mixed | DeepSeek-V4-Flash | GLM-5.2 | gpt-oss_120b | Slot-1 rate (ds, glm, j3) |
|---|---|---|---|---|---|---|
| v0 (unedited, origin/main) | 0.562 [0.487, 0.637] | 7 / 2 / 31 | 0.537 | 0.525 | 0.588 | 0.71, 0.88, 0.86 |
| ship (edited) | 0.588 [0.512, 0.662] | 9 / 2 / 29 | 0.525 | 0.562 | 0.575 | 0.65, 0.86, 0.82 |

Paired ship minus v0: +0.025 [-0.075, +0.125] (9 tickets up, 7 down).

Decision: the preregistered rule needs the paired lower bound above 0; it is -0.075, so the edit is not shown to help and does not ship. `SKILL.md` and its eval were reverted to the branch base. No superiority claim over Superpowers is made: the unedited skill's lower bound is 0.487, and the edited arm's 0.512 is for a text that does not ship. All three judges are position-biased (slot-1 rates 0.65 to 0.88), so 29 to 31 of 40 tickets are 0.5 under strict agreement. At n=40 a true lift of +0.075 would usually leave the lower bound below 0, so this reads "not shown", not "shown harmful". The round-1 40-ticket numbers are contaminated; see `../delivery-r1-1017/ERRATA.md`.

Files: `bench.py`, `run.sh`, `prompts/` (seeds, v0, ship), `tickets.json`, `outputs/<arm>/<ticket>.txt`, `judge/<judge>/<arm>__sp/<order>/<ticket>.json`, `ledger.jsonl`. Score with `python3 -I bench.py score v0 sp` and `... score ship sp`, then `... paired v0 ship` (writes `results/`, not committed). Re-run needs `PCSS_KEY` in the environment.

## Review notes

- **Preregistration hash.** The `preregistered` ledger entry (line 1, 2026-10-17T21:32:56Z) hashes the first 10 lines of `SHA256-frozen.txt`: `head -10 SHA256-frozen.txt | shasum -a 256` gives `3082bbec…`, which matches. The 11th line (`tickets.json`) was appended after the ticket writer ran, at the `tickets_frozen` ledger event (line 43). The tickets were therefore generated after preregistration, as the protocol intends, and frozen before any plan was generated.
- **v0 prompt.** `prompts/v0.txt` is the `origin/main` `SKILL.md` at the time of the run (1.590.0). It differs from the current `origin/main` only in the `version:` line (1.591.0).
