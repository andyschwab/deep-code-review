Business-ops shipped text on the c150 scenarios, 2026-10-18. Preregistration: PREREGISTERED.md; hashes in SHA256-frozen.txt; append-only ledger.jsonl (first line `preregistered`). All calls on the PCSS endpoint, $0. Rival text is MIT, notice in ../bizops-e-confirm-1018/LICENSE.rival.txt.

Question: docs/perun-vs-rivals.md cited 0.563 for frozen text e (../bizops-e-confirm-1018), but the SKILL.md shipped at origin/main 06e6fa48 (sha256 39af659d...) differs from e by 16 lines (reworded frontmatter description, two changed Verification bullets) and was never benched as shipped. This runs the shipped text itself. Descriptive check, not a keep decision; no SKILL.md edit.

Same 150 scenarios, same generator (Qwen3.5-397B-A17B, temperature 0.3), same judge (judge v2, GLM-5.1, both orders, strict agreement else 0.5, bootstrap 10,000 seed 1; slot-1 rate 0.513, 0 failed orders), same rival answers (committed files of the earlier round, reused):
  shipped              0.580 [0.507, 0.650]   75 wins / 24 ties / 51 losses
  e (earlier round)    0.563 [0.490, 0.633]
  v0 (earlier round)   0.473 [0.397, 0.547]
  paired shipped - e   +0.017 [-0.037, 0.073]
  paired shipped - v0  +0.107 [0.040, 0.173]
The shipped text scores the same as e within noise on these 150 scenarios, and above v0. The shipped lower bound 0.507 is barely above 0.5 and no superiority rule was preregistered for this run, so it is not a claimed win. Shipped and e are separate unseeded generations, so the paired CI includes sampling noise; it does not show the 16 lines are neutral.

Reproduce: python3 -I bench.py run, then bench.py paired (committed outputs/ and judge/ are cached and reused). Scenarios, rival outputs and the e / v0 results are read from ../bizops-e-confirm-1018, not copied.
