Shipped business-ops SKILL.md vs its rival on 200 fresh held-out scenarios, 2026-10-18. Preregistration: PREREGISTERED.md; hashes in SHA256-frozen.txt; append-only ledger.jsonl (first line `preregistered`, written after the scenarios were frozen and before any arm answer). All calls on the PCSS endpoint, $0. Rival text is MIT, notice in ../bizops-e-confirm-1018/LICENSE.rival.txt.

Rule fixed in advance: claim superiority iff the win-rate 95% CI lower bound is above 0.5 (and the judge slot-1 rate is within 0.4 to 0.6).

Result (GLM-5.1 judge v2, both orders, bootstrap 10,000 seed 1):
  shipped (sha256 39af659d...) vs rival (sha256 b0318f64...)   0.463 [0.403, 0.522]   72 wins / 41 ties / 87 losses
  slot-1 rate 0.537 (healthy), 0 failed judge orders
  superiority: NO. The point estimate is below 0.5 and the interval lower bound is 0.403.
For context only, never pooled: the same text scored 0.580 [0.507, 0.650] on the c150 scenarios (../bizops-shipped-1018), which were not fresh for it. This fresh test does not reproduce that.

Scenarios: scenarios-heldout.json, ids s200-001 to s200-200, mechanically disjoint (id, text, 6-word shingles <= 0.10) from every JSON scenario set under docs/bench and scripts/eval-fixtures (`bench.py check`). Settings: prompts/seeds_business-ops.txt.
Reproduce: python3 -I bench.py run (committed outputs/ and judge/ are cached and reused).

Post-freeze amendment (SHA256-amend.txt, ledger event bench_amended): scenario s200-050 named a city that the privacy banlist matches as a personal name; the city name was replaced by another city in scenarios-heldout.json only. All verdicts and outputs used the original text; the judge cache for that one scenario will not hit on a re-run. Nothing else changed.
