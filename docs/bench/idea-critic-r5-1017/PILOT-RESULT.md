# Pilot result (recorded 2026-10-17, before the tune run)

Round-4 v0 and RIVAL answers on the 40 round-4 held-out scenarios (copied, not regenerated), judged by GLM-5.1, GLM-5.2 and gpt-oss_120b in both orders. Records: `judge5/v1/pilot/`, `judge5/v2/pilot/`; results: `results5-v0-pilot-v1.json`, `results5-v0-pilot-v2.json`.

| judge prompt | order-disagreement rate | wins / ties / losses (v0) | slot-1 rate GLM-5.1 / GLM-5.2 / gpt-oss_120b |
|---|---|---|---|
| v1 (round 4 prompt) | 0.458 | 6 / 23 / 11 | 0.675 / 0.725 / 0.562 |
| v2 (work first) | 0.300 | 12 / 14 / 14 | 0.425 / 0.600 / 0.550 |

Rule from PREREGISTERED.md section 2: v2 is adopted because its order-disagreement rate (0.300) is lower than v1's (0.458) on the same pairs. Ties fall from 23 to 14 of 40. Win rate was not a selection criterion (v0 is 0.438 under v1 and 0.475 under v2, both near the rival).

Run notes: the first launch was a detached background run whose requests were all refused by the sandbox network (URLError, visible in `ledger.jsonl`), so it wrote no judge record; the runs above were started again in the foreground. One scenario per prompt ended incomplete on the first pass (a call failed twice, so no record was written) and was completed by a rerun.
