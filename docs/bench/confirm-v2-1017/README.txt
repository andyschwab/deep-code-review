Confirmation run, 2026-10-17: agentic-ceo, positioning and product-discovery against their rivals on a fresh held-out n=60 each,
judge protocol v2 (reason-first, neutral labels, both orders, chain GLM-5.1 / GLM-5.2 / gpt-oss_120b), generator Qwen3.5-397B-A17B,
all PCSS, spend $0. No skill, rival, harness or judge text was edited.

Result (PASS = 95% CI lower bound above 0.5), judge GLM-5.1 for all three (slot-1 rate inside 0.4 to 0.6, so GLM-5.2 and
gpt-oss_120b were never needed and have no verdicts):
  agentic-ceo        0.733 [0.642, 0.825] PASS  win 36 tie 16 loss 8   slot-1 0.517  vs obra/superpowers using-superpowers
  positioning        0.650 [0.550, 0.742] PASS  win 29 tie 20 loss 11  slot-1 0.542  vs deanpeters positioning-statement
  product-discovery  0.692 [0.592, 0.783] PASS  win 34 tie 15 loss 11  slot-1 0.558  vs phuryn pm-skills
Per-scenario scores, outputs and cached judge verdicts: run/<skill>/heldout-*/. Recompute check: scripts/test_confirm_v2.py.

Order of events (hashes: SHA256-prereg.txt before any seed; SHA256-frozen.txt after scenarios, before any answer):
1. PREREGISTERED.md written and hashed. 2. confirm.py seeds, then scenarios (fixtures/<skill>/). 3. frozen hashes. 4. run.
Deviations, stated plainly:
- confirm.py was patched after the prereg hash and before any answer existed: the scenario writer's output parsing (it sometimes
  wraps the array or drops the brackets) and a rewrite-the-offender step for within-set overlap. SHA256-frozen.txt holds the final hash.
- run-aborted-urlerror/ is a first attempt whose detached process lost network: every generation call failed with URLError, so
  nothing was generated or judged. It is kept as a record, not deleted; the real run is run/.
- Rival text is fetched at run time and recorded by hash only (the positioning rival is CC BY-NC-SA, not vendored).
Limits: one generator family wrote the scenarios and all answers; judges are models; scenarios are fictional. PASS means "beats this
rival on this synthetic distribution under this judge", not a claim about real users.
Review notes (independent review of PR #1643; all numbers recomputed exactly from the judge files):
- SHA256-prereg.txt records confirm.py at f3cf42…; the committed confirm.py hashes to 442b92… because of the patch described above.
  There is no timestamped ledger, so "patched before any answer existed" rests on this README, not on a machine record.
- scripts/test_confirm_v2.py checks results.json for internal consistency; it does not recompute from the judge files. The
  independent recompute from judge files is what verifies the headline numbers. The frozen-hash test covers the held-out and
  seed files only.
- Rival fixtures name the upstream default branch, not a commit; the recorded SHA-256 of the fetched text is the only pin.
- Judge files store the verdict only; the judge's written reasoning was not kept.
