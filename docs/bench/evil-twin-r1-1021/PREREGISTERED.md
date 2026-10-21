# Pre-registration: evil-twin bench R1 (frozen before any model call)

Question: does the `idea-critic` skill (the evil twin) catch a planted fatal flaw in a proposal more often than no skill, and more often than a generic "brainstorm pros and cons, then recommend" prompt, without falsely killing sound proposals?

## Frozen inputs
`SHA256-frozen.txt` lists the driver `scripts/evil_twin_bench.py`, `cases.txt` (corpus plus hidden answer keys), `skill-arm.txt` (a byte copy of `.claude/skills/idea-critic/SKILL.md` at the base commit), `brainstorm-arm.txt` (the generic prompt, wording written for this bench, no third-party text) and this file. The first line of `ledger.jsonl` is the hash of that list, written before the first model call. The driver imports the shared PCSS client `scripts/rival_eval.py` (chat transport only; it does not shape any prompt or score).

- Hypothesis: the skill text raises flaw recall over no skill and over the brainstorm prompt, at no more than one extra false kill among six controls.
- Corpus: 30 fictional proposals (Acme-style names, invented numbers, no real parties). 24 each hide one fatal flaw that is findable from the proposal text; 6 are sound controls. Written by the Perun side before the freeze; no case was run against any arm first. Order interleaves controls.
- Arms (same system prefix and same user prompt; only the guidance block differs): `none`; `perun` (skill text appended as "Follow this guidance"); `brainstorm` (the generic prompt appended the same way).
- Generator: `Qwen3.5-397B-A17B` on the free PCSS endpoint, non-thinking, temperature 0, one generation per case and arm, max 2,500 tokens. Judge: `GLM-5.1`, a different model, non-thinking, temperature 0, sees the proposal, the hidden key and one response, never the arm name. Scores `FLAW_CAUGHT` (the response names the keyed flaw and treats it as blocking) and `KILLED` (the response recommends rejecting or holding). No paid call, public fictional data only.
- Statistics: recall = mean `FLAW_CAUGHT` over the 24 flawed cases; false-kill = mean `KILLED` over the 6 controls; unparsed judge output counts as 0 and is tallied. Percentile bootstrap, 10,000 resamples, seed 1, cases resampled within flawed and within control; contrasts are paired.

## Verdict (`verdict()` in the driver, evaluated once)
- INVALID if any arm has more than 2 unparsed judge outputs. INCONCLUSIVE if the `none` recall is 0.90 or higher (no headroom).
- Primary: lower bound of the `perun` recall 95% CI is above the `none` recall point estimate.
- Guard: `perun` false-kill is at most the `none` and `brainstorm` false-kill plus 1/6 (one control).
- WIN: primary and guard hold and the paired `perun - brainstorm` recall interval has a lower bound above 0. TIE: primary and guard hold but not that. REVERT: otherwise.
- Keep rule: only WIN or TIE keep the skill as is; REVERT means the skill text is not shown to help on this corpus. The skill text is not edited by this bench in any case.

## Known limits (declared up front)
n = 24 flawed and 6 controls, so the false-kill interval is wide and the guard is coarse. One generator, one judge, one generation per cell. The skill's `references/` files are not available to the model. The judge sees response style, so it is not fully blind to the arm in practice. Flaws were planted by the same side that wrote the skill, so the corpus can favor flaw classes the skill names. Results describe this corpus, not proposals in general.
