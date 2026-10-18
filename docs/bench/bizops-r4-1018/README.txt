Round 4 on the business-ops SKILL.md, 2026-10-18: one candidate edit against the shipped text and the marketingskills pricing rival, 150 fresh held-out scenarios. Preregistration: PREREGISTERED.md; hashes in SHA256-frozen.txt; ledger.jsonl line 1 `preregistered` (sha256 of SHA256-frozen.txt) was written after the scenarios were frozen and before any held-out answer. Tune records (spent sup-1018 scenarios, three candidates a, b, c) are in ledger-tune.jsonl and tune/. All calls on the PCSS endpoint, $0. Rival text is MIT, notice in ../bizops-e-confirm-1018/LICENSE.rival.txt.

Rules fixed in advance: ship the edit iff the paired (edit minus shipped) 95% CI lower bound is above 0; claim superiority iff the edit's win-rate CI lower bound against the rival is above 0.5 (and judge slot-1 rate within 0.4 to 0.6).

Result (GLM-5.1 judge v2, both orders, bootstrap 10,000 seed 1, n=150, 0 failed judge orders):
  edit (variant b) vs rival     0.503 [0.433, 0.573]   61 wins / 29 ties / 60 losses, slot-1 rate 0.517
  shipped vs rival              0.507 [0.437, 0.577]   60 wins / 32 ties / 58 losses, slot-1 rate 0.535
  paired edit minus shipped     -0.003 [-0.063, 0.060]
  ship edit: NO (lower bound -0.063 is not above 0). Win claim: NO (lower bound 0.433). SKILL.md is unchanged.
The tune gain of variant b (+0.055 [0.005, 0.107] on the spent set) did not carry over: it was chosen on that set and is selection-biased. Variants a and c were not tested held-out. The shipped text's 0.507 here and 0.463 in ../bizops-sup-1018 are two different fresh sets, never pooled.

Reproduce: python3 -I bench.py run (committed outputs/ and judge/ are cached and reused); tune: python3 -I bench.py tune.
