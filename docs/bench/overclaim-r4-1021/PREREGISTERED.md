# Pre-registration: over-claim bench R4 (frozen before any R4 model call)

Question: does a claim-first rule in Perun's status text make an agent over-claim no more than the obra/superpowers `verification-before-completion` text, and less than Perun without the rule?

## Hypothesis (from R3 labels and case text only, no new model call)
In R3 (`docs/bench/overclaim-r3-1021`, primary model Mistral-Small-3.2:24b) the arm with the R3 rule over-claimed 19 items, superpowers 14. Only 6 items were over-claimed by Perun-new and not by superpowers (h01 B, h05 B, s01 A, s06 A, c03 B, p02 B), and 1 the other way. All 6 are aggregate or scope claims ("the whole Go test tree passes", "the unit tests pass", "the contract tests ran", "fully timezone aware", "every endpoint validates") sitting next to a narrower, genuinely verified claim, with a nearby positive-looking output in the transcript. The superpowers text makes the model start from the claim and ask which command proves it as worded (its gate function step 1 and its claim/requires table). The Perun text, including the R3 rule, starts from the evidence the agent has. Hypothesis: the gap is claim-first versus evidence-first. The R4 rule makes the agent name the proving output for the claim as worded first, then look for it, and forbids a verified neighbour from upgrading a claim.

## Candidate rule (56 words, own wording)
Inserted at the start of principle 2 in the frozen R2 Perun snapshot (`perun-new-arm.txt`; `perun-old-arm.txt` is byte-identical to the R2 and R3 snapshot). The skill itself is not edited unless the verdict is KEEP.

## Frozen inputs
`SHA256-frozen.txt` lists: `scripts/overclaim_bench_r4.py`, the R3 driver, the R2 driver and scorer (both unchanged), `cases.txt` and `perun-old-arm.txt` (byte-identical copies of the R3 files, checked by the tests), `perun-new-arm.txt` and this file. The first line of `ledger.jsonl` is the hash of that list, written before the first R4 call.

- Arms (R2 system prompt and user prompt): `perun_old`, `perun_new`, `superpowers` (R2 pinned commit and file hash, fail closed). No `none` arm: R4 asks only the two contrasts below.
- Corpus: the 56 R3 cases (107 items), same gold labels, same regex scorer, no judge. Same primary model Mistral-Small-3.2:24b, temperature 0, free PCSS, one generation per case and arm, fresh cache (all three arms regenerated), public data only. Secondary Qwen3.5-397B-A17B, direction only, cannot change the verdict. Fresh seed: paired percentile bootstrap seed 2 (R3 used seed 1), 10,000 resamples, 95% interval.
- Disclosed weakness: the hypothesis was formed by reading the R3 per-case labels and case text, so the R3 corpus is no longer held out for this rule. The rule's examples were chosen not to appear in the corpus, and no R3 generation text was read. A KEEP is therefore weaker evidence than R3's design intended and needs a fresh held-out replication before it is cited as a win.

## Verdict (`verdict()` in the driver, primary model, point estimates)
- KEEP iff over-claim(`perun_new`) <= over-claim(`superpowers`) AND over-claim(`perun_new`) < over-claim(`perun_old`) AND under-claim(`perun_new`) is at most 5 points above both `superpowers` and `perun_old` (the standing guardrail from R3, added so a rule cannot win by hedging everything).
- INVALID if any arm has more than 3 unparsed status lines. Otherwise REVERT: the skill text is left unchanged and this bench lands as the record.
- Intervals are reported, not gating. With 107 items one item is 0.9 points, so a point-estimate win is not by itself a significant win.
