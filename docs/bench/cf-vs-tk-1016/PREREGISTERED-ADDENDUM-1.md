# Addendum 1 (2026-10-16): recall-recovery variants, tune/held-out split

Written BEFORE any variant run. The first-run result (n=43, from results.json) motivates it: CF precision .780 vs TK .644 (+.137, CI [+.032, +.247]) but adjudicated recall .488 vs .628 (-.140, CI [-.256, -.047]). Goal: a CF variant that keeps a precision lead over TK and loses no recall.

## Split (deterministic; frozen in split.json)
Sort the 43 train case ids by sha256(id, UTF-8) hex ascending. First 21 = TUNE, last 22 = HELDOUT. split.json lists both.

## Variants (prompts frozen in prompts/, SHA-256 recorded in prompts/SHA256SUMS-variants)
- CF60 (prompts/cf60_system.md): CF card with the confidence floor lowered from 80 to 60 (floor line, schema range, empty-array line).
- CFDIFF (prompts/cfdiff_system.md): CF card, floor 80, plus one sentence in step 3: when the code a finding depends on is not visible (patch-only workspace), judge from the diff itself instead of dropping the finding; a mechanism visible in the diff counts as verified.
- CFHUNT (prompts/cfhunt_system.md): CF card, floor 80, plus one paraphrased checklist line (step 5b) covering the bug-hunting categories of TK's Bug Detection paragraph (control flow/business rules, unguarded null/empty values, concurrent interleaving, unreleased resources, exploitable security gaps, costly hot-path work, missing serious error handling), in new wording.

## Procedure
1. Run each variant on the TUNE half only (same producer prompt, model, flags, workspace, judge and verify prompt as PREREGISTERED.md; one run per case). TK tune-half results are reused from the existing outputs (no rerun).
2. Metrics per the original definitions: verified precision (pooled good/findings), adjudicated recall (credited/bugs), F1 = 2PR/(P+R) of those two pooled values.
3. SELECTION: among variants whose tune-half precision >= TK's tune-half precision (point values), choose the highest tune-half F1. Ties: higher precision, then fewer findings. If no variant qualifies, stop: no held-out run, report FAIL (no variant).
4. Run ONLY the chosen variant on the HELDOUT half; compare with TK's existing held-out outputs (and original CF, for reference only).
5. Held-out decision (paired case-level bootstrap, 10000 resamples, seed 1, pooled-ratio statistics recomputed per resample, 95% percentile CI), as written by the owner: PASS iff point recall diff (variant - TK) >= -0.03 AND point precision diff > 0. Also reported: precision/recall/F1 diffs with CIs, and whether the precision CI lower bound > 0 ("significant lead"), which is reported but not part of the PASS rule.
6. Errored cases are dropped from both arms (paired) and listed.

## Budget
Cap $15 on the shared ledger.jsonl (total ledger sum, which already holds the first run's ~$3.5, so the cap is strictly tighter than $15 of new spend). Cap checked before every call with in-flight reserve; hitting it = INCOMPLETE. Foreground, jobs=4, no plan-usage gate.

## Known limits
Selection on 21 cases is noisy; a single run per variant per case; judge is Claude-family; tune-half re-use of TK outputs means TK is a fixed baseline; the held-out half is touched once.
