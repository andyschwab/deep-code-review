Baseline run, 2026-10-18: growth-analytics and product-output-safety against their H1 rivals on a fresh held-out n=60 each,
judge protocol v2 (reason-first, neutral labels, both orders, chain GLM-5.1 / GLM-5.2 / gpt-oss_120b), generator Qwen3.5-397B-A17B,
all PCSS, spend $0. No skill, rival, harness or judge text was edited. Protocol cloned from docs/bench/confirm-v2-1017.

Result (PASS = 95% CI lower bound above 0.5), judge GLM-5.1 for both (slot-1 rate inside 0.4 to 0.6, so GLM-5.2 and gpt-oss_120b
were never needed and have no verdicts). Both skills FAIL; both point estimates are below 0.5:
  growth-analytics       0.442 [0.333, 0.550] FAIL  win 18 tie 17 loss 25  slot-1 0.558  vs marketingskills analytics and ab-testing
  product-output-safety  0.467 [0.350, 0.583] FAIL  win 23 tie 10 loss 27  slot-1 0.475  vs promptfoo redteam-setup
No skill is shown superior to its rival on this set; neither CI excludes parity with the rival (0.5) in either direction.
Per-scenario scores, outputs and cached judge verdicts: run/<skill>/heldout-*/. Summary: run/summary.md.

Order of events (hashes: SHA256-prereg.txt before any seed; SHA256-frozen.txt after scenarios, before any answer):
1. PREREGISTERED.md and bench.py written and hashed (SHA256-prereg.txt). 2. bench.py seeds, then scenarios (fixtures/<skill>/, and
scenarios-heldout-<skill>.json, a byte copy of fixtures/<skill>/heldout.json that scripts/bench_check.py reads). 3. SHA256-frozen.txt.
4. ledger.jsonl "preregistered" event holding the sha256 of SHA256-frozen.txt. 5. run (events run_start and run_done follow).

Deviations from confirm-v2-1017, stated plainly:
- Writer batches are 10 scenarios, not 6, so each skill's writer brief runs verbatim ("exactly 10"). Ids are prefixed ga and po.
- Seeds and scenarios (step 2) were generated after the prereg hash and before the frozen hash, so they sit outside the ledger
  (bench_check.py needs the ledger event to hash SHA256-frozen.txt, which lists the scenarios). Both hash files are kept.
- The rewrite-the-offender step for within-set overlap writes one scenario with the brief's count replaced by 1; for
  product-output-safety that single rewrite would not carry the brief's pressure-to-overclaim position. bench.py does not log whether any rewrite fired.
- Rival texts are the committed ones under docs/bench (marketingskills analytics and ab-testing, promptfoo redteam-setup).
Limits: one generator family wrote the scenarios and all answers; judges are models; scenarios are fictional. A FAIL here means
"not shown to beat this rival on this synthetic distribution under this judge", not a claim about real users.
