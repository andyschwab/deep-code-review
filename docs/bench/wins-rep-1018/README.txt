Replication run, 2026-10-18: agentic-ceo, positioning and product-discovery against their rivals on a fresh held-out n=150 each,
second look at the three wins first measured in ../confirm-v2-1017 (n=60). Same method: judge protocol v2 (reason-first, neutral labels,
both orders, chain GLM-5.1 / GLM-5.2 / gpt-oss_120b), generator Qwen3.5-397B-A17B, all PCSS, spend $0, no claude -p. Rule fixed in
PREREGISTERED.md before any seed: CI lower bound above 0.5 keeps "Win", else the docs row is downgraded.

Result (judge GLM-5.1 for all three; slot-1 rate inside 0.4 to 0.6, so GLM-5.2 and gpt-oss_120b were never needed). n=150, no errors:
  agentic-ceo        0.637 [0.577, 0.697] PASS  win 70 tie 51 loss 29  slot-1 0.583  (first run 0.733 [0.642, 0.825])
  positioning        0.737 [0.680, 0.790] PASS  win 90 tie 41 loss 19  slot-1 0.507  (first run 0.650 [0.550, 0.742])
  product-discovery  0.690 [0.633, 0.747] PASS  win 77 tie 53 loss 20  slot-1 0.563  (first run 0.692 [0.592, 0.783])
Per-scenario scores, outputs and cached judge verdicts: run/<skill>/heldout-*/. Combined summary files: run/summary-<skill>.{json,md}
(the three skills ran as three parallel processes, so there is no single summary.json).

Arms: SKILL.md byte-identical to the base commit (hashes in SHA256-frozen.txt). positioning and product-discovery are byte-identical to
the confirm-v2-1017 arms; agentic-ceo differs by one later wording-only commit (ba7b3624). Rival text hashes equal the confirm-v2-1017 records.

Order of events: 1. PREREGISTERED.md written and hashed (SHA256-prereg.txt). 2. confirm.py seeds, then scenarios (fixtures/<skill>/).
3. SHA256-frozen.txt written and its hash recorded as line 1 of ledger.jsonl. 4. run, three skills in parallel. The set was frozen
before any answer or verdict existed. Disjointness: ids w001 to w150 collide with no id in any other docs/bench scenario file;
scripts/bench_check.py passes; the writer rejects any scenario above 10% shared 6-word shingles with the docs/bench corpus or another new scenario.

Deviations, stated plainly (both made after the prereg hash and before any scenario or answer existed; SHA256-prereg.txt holds the
earlier confirm.py hash, SHA256-frozen.txt the final one):
- The first scenario pass aborted: one agentic-ceo seed batch (seeds 139 to 144) failed every try on the overlap rule (8 tries, then 12 after a first patch). confirm.py
  was patched so only rejected seeds are re-asked, and a seed still rejected after 6 tries is replaced by a freshly drawn seed (same
  near-duplicate check as the seed step). Four agentic-ceo seeds (067, 103, 139, 145) were replaced; the final seeds.txt holds the
  replacements. Scenario text from the aborted passes was discarded, never used, never judged.
- The overlap rule is applied to the share rounded to two decimals (`round(overlap, 2) <= 0.10` in confirm.py, inherited from
  confirm-v2-1017), so a scenario up to 0.104 shared 6-word shingles passes, not strictly at most 10% as PREREGISTERED.md says.
  Recomputed against the corpus without this bench, three scored held-out scenarios sit above 0.100 (positioning w070 0.101,
  positioning w127 0.104, product-discovery w127 0.104) and two unscored tune scenarios do (0.116, 0.117).
- Rival text is fetched at run time and recorded by hash only (the positioning rival is CC BY-NC-SA, not vendored).
Limits: one generator family wrote the scenarios and all answers; one judge scored all three skills; scenarios are fictional. PASS means
"beats this rival on this synthetic distribution under this judge", not a claim about real users. There is no machine timestamp
for the prereg hash (ledger.jsonl line 1 is the frozen-set hash and its time).
