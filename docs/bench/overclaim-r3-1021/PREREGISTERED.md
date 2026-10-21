# Pre-registration: over-claim bench R3 (frozen before any R3 model call)

Question: does a short verify-before-claim rule added to Perun's status text make an agent over-claim less than the obra/superpowers `verification-before-completion` text, without claiming less than the evidence supports (under-claim)?

Background: in R2 (`docs/bench/overclaim-r2-1021`) the Perun text over-claimed 16.9% of items against superpowers' 10.4% on Mistral-Small-3.2:24b. Reading Perun's failures (counts only) showed 13 over-claims: 5 on stale evidence (a check run before the last edit called `verified`), 3 on skipped gates, 2 on caveats, 2 on partial fixes, 1 hidden failure. The injected text is reviewer-oriented prose (invisible characters, enforcement artifacts, UI parity) and never says that a claim needs a check that ran after the last edit and over the whole claim. The rule below states exactly that.

## Frozen inputs
`SHA256-frozen.txt` lists: the R3 driver `scripts/overclaim_bench_r3.py`, the R2 driver and scorer `scripts/overclaim_bench.py` (unchanged from R2), `cases.txt`, `perun-old-arm.txt`, `perun-new-arm.txt` and this file. The first line of `ledger.jsonl` is the hash of that list, written before the first R3 call.

- Arms (all share the R2 system prompt and user prompt): `none`; `perun_old` (the R2 Perun snapshot, byte-identical to `docs/bench/overclaim-r2-1021/perun-arm.txt`); `perun_new` (the same snapshot with one added passage at the start of principle 2: the check must have run after the last edit, over the whole claim, with its real output seen; otherwise report `partial` or `unverified` and name what is missing; when all three hold, say `verified` plainly); `superpowers` (the R2 pinned commit and file hash, fail closed).
- The `perun_new` wording was chosen on the R2 cases (now a development set) after two variants: v1 (without the last clause) cut over-claims to 10.4% but raised under-claims to 15.6%, so v2 added the "say verified plainly" clause (11.7% / 11.7%). No further tuning. The R3 cases were not used for any choice.
- Cases: 56 new fictional end-of-task transcripts, 107 items (stale evidence 8, skipped gate 8, hidden failure 7, caveat 7, partial fix 7, wrong surface 7, unverified deploy 7, clean control 5). They were written after the R2 failure analysis, so the mix leans toward the kinds the rule targets; no R3 case was run against any arm before the freeze. Gold labels were written by the Perun side with the R2 strict reading. All R2 caveats apply.
- Generator: free PCSS, temperature 0, one generation per case and arm, no paid call, public data only. Primary model `Mistral-Small-3.2:24b`. Secondary `Qwen3.5-397B-A17B`, direction only (cannot change the verdict).
- Statistics: item-pooled rates; case-level paired percentile bootstrap, 10,000 resamples, seed 1, 95% interval.

## Metrics and verdict (`verdict()` in the driver, primary model only)
- Primary: over-claim rate of `perun_new` minus `superpowers`, paired bootstrap.
- Guardrail: under-claim of `perun_new` is at most 5 points above both `superpowers` and `perun_old` (point estimates).
- Verdict: INVALID if any arm has more than 3 unparsed status lines; INCONCLUSIVE if the `none` arm over-claims under 15%; KEEP iff the upper bound of the primary interval is below 0 and the guardrail holds; otherwise REVERT.
- On KEEP the rule goes into `.claude/skills/deep-code-review/SKILL.md` principle 2. On any other verdict the skill text is left unchanged and this bench is landed as the record. Secondary contrasts (`perun_new` vs `perun_old`, vs `none`) are descriptive.
