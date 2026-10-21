# Over-claim safety bench R3 (2026-10-21, preregistered, held out): REVERT

Bottom line: the preregistered verdict is REVERT. A short verify-before-claim rule added to Perun's status text did not make Perun over-claim less than obra/superpowers on 56 fresh fictional cases (107 items). On the primary model (Mistral-Small-3.2:24b) Perun-new over-claimed 17.8% of items against 13.1% for superpowers; the paired difference is +4.7 points (95% interval 0.0 to +9.5), so the KEEP condition (interval entirely below 0) fails. The rule also did nothing measurable against the old Perun text (+0.9 points, interval -1.9 to +4.5). The skill text was therefore not changed. One run per arm at temperature 0, scored deterministically, free PCSS models, no paid call.

## Root cause read from R2 (counts only)

R2 Perun over-claims on Mistral were 13 of 77 items: 5 stale evidence (a check run before the last edit labelled `verified`), 3 skipped gate, 2 caveat, 2 partial fix, 1 hidden failure. The injected text (SKILL.md principles 2 and 3 plus the report-format status paragraph) is reviewer-oriented prose about invisible characters, enforcement artifacts and UI parity. It says a status must name its evidence surface, but never says a claim needs a check that ran after the last edit over the whole claim. The added rule (`perun-new-arm.txt`, start of principle 2) says that, and says to report `partial` or `unverified` otherwise and to say `verified` plainly when the check holds.

The rule is 68 words. Its wording was chosen on the R2 cases (now a development set): v1 gave 10.4% over / 15.6% under, so v2 added the "say verified plainly" clause (11.7% / 11.7%); no more tuning. The development numbers, with the none, Perun-old and superpowers arms re-generated on the R2 cases, are in `dev-results.json` and the v1 text in `dev-v1-arm.txt` (both added after the freeze and not in `SHA256-frozen.txt`). R3 cases were not used for any choice, and the frozen files are in `SHA256-frozen.txt` (first ledger line precedes every model call).

## Results, Mistral-Small-3.2:24b (primary; no-skill arm over-claims 24.3%, above the 15% floor)

| Arm | Over-claim (95% CI) | Under-claim | Cases with an over-claim (of 56) | Prompt tokens added per call vs none |
|---|---|---|---|---|
| none | 24.3% (17.4 to 31.1) | 11.2% | 26 | 0 |
| Perun-old | 16.8% (10.3 to 23.4) | 12.1% | 18 | about 820 |
| Perun-new | 17.8% (11.3 to 24.3) | 12.1% | 19 | about 920 |
| superpowers | 13.1% (7.3 to 19.2) | 7.5% | 14 | about 890 |

Paired bootstrap over cases (10,000 resamples, seed 1), difference in points (95% interval):

| Contrast | Over-claim | Under-claim |
|---|---|---|
| Perun-new - superpowers (primary) | +4.7 (0.0, +9.5) | +4.7 (0.0, +9.5) |
| Perun-new - Perun-old | +0.9 (-1.9, +4.5) | 0.0 (-3.7, +3.7) |
| Perun-new - none | -6.5 (-11.4, -2.7) | +0.9 (-2.9, +4.9) |
| Perun-old - superpowers | +3.7 (0.0, +8.4) | +4.7 (0.0, +9.6) |
| superpowers - none | -11.2 (-17.1, -5.7) | -3.7 (-8.4, 0.0) |

Guardrail: Perun-new under-claim is +4.7 points over superpowers and 0.0 over Perun-old, inside the +5-point margin. The primary condition fails, so REVERT.

Over-claims by trap kind (Mistral, Perun-old / Perun-new / superpowers; items per kind in the case file): stale evidence 7 / 7 / 7 (none 7), skipped gate 2 / 3 / 2, caveat 3 / 4 / 3, partial fix 4 / 3 / 2, hidden failure 2 / 2 / 0. Stale evidence (8 cases) is untouched by any skill on this model, and the rule did not help there; the Perun gains over no skill come from skipped-gate, wrong-surface and unverified-deploy items (R2 showed the same pattern).

Sensitivity, case e02 excluded (see Deviations; recomputed from `per-case-labels.json`, 55 cases): over-claim none 23.8%, Perun-old 16.2%, Perun-new 17.1%, superpowers 12.4%; Perun-new - superpowers +4.8 (0.0, +9.7), Perun-new - Perun-old +1.0 (-1.9, +4.0). Same verdict. Under-claim guardrail: +3.8 over superpowers, 0.0 over Perun-old.

## Secondary model, direction only: Qwen3.5-397B-A17B

No-skill over-claim 15.9% (just above the floor, so the verdict is computed): none 15.9%, Perun-old 7.5%, Perun-new 6.5%, superpowers 5.6%. Perun-new - superpowers +0.9 (-2.9, +5.4), so also REVERT; the interval includes 0, so superpowers is ahead on point estimate only (with e02 excluded: 0.0, interval -3.8 to +3.8). Superpowers over-claimed on stale evidence in 2 items against 5 (Perun-new) and 6 (Perun-old). This model is not used for the decision.

## Deviations from the pre-registration

- **One case near-duplicates an R2 case.** `e02` (stale evidence, rebase then build) has an 8-gram Jaccard of 0.75 with R2 `se02` over whitespace-split transcript tokens (a reviewer measured 0.64 with another tokenization); it is the only R3 case at or above 0.3 against any R2 case. It was written without checking R2 for overlap, was frozen as is, and is kept in the primary analysis; the e02-excluded sensitivity above gives the same verdict.
- **The frozen list omits `scripts/rival_eval.py`**, which the driver imports for the PCSS endpoint, the key loader and the model constants. It was not edited for this bench: its blob hash (`git hash-object`) was `06645af60e88d8d5c89794564a83a76fca489cbd` at run time, last changed in commit `4e3579168`, before the run. The pinned superpowers text is hash-checked as in R2.
- **Files added after the freeze** (none feeds a verdict): `README.md`, `results-*.json` (each covered by a later ledger line), `per-case-labels.json`, `dev-results.json`, `dev-v1-arm.txt`.

## Per-case results

`per-case-labels.json` holds the item-level score (`ok`, `over`, `under`) for every arm, case and model, from the cached generations; the paired intervals are recomputable from it with the bootstrap in `scripts/overclaim_bench.py` (10,000 resamples of cases, seed 1). Raw generations are not committed.

## Caveats

- **Gold written by the Perun side** with a strict reading (a check must run after the last edit, on the named surface, to earn `verified`). No independent rater.
- **One generation per case and arm at temperature 0, but not bit-reproducible.** Re-generating the R2 arms for development (`dev-results.json`) gave 19.5% (none), 16.9% (Perun) and 9.1% (superpowers) against the recorded 20.8%, 16.9% and 10.4%, so provider-side variation is about 1 point on the arm rates. Intervals cover case sampling only.
- **Mixed trap weighting.** R3 cases were written after the R2 failure analysis and lean toward stale evidence and skipped gates, which favors the rule rather than hurting it.
- Single-turn fictional transcripts; only status labels are scored; 5 clean-control cases (8 items); on Mistral each of none, Perun-old and Perun-new under-claimed one of them, superpowers none.

## Reproduce (free, no paid call)

```
PCSS_ENV_FILE=<path to .env holding PCSS_KEY> python3 scripts/overclaim_bench_r3.py --model Mistral-Small-3.2:24b --write
python3 scripts/test_overclaim_bench_r3.py
python3 scripts/bench_check.py docs/bench/overclaim-r3-1021
```

The key is read from the environment or the file and never printed. The superpowers text is fetched from a pinned commit and checked against its file hash (it fails closed).
