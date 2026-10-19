# Differentiator bench: fabrication rate on bait prompts (2026-10-19)

BLUF: tie. On 25 held-out bait prompts, the business-ops skill prompt, one public rival prompt and a plain prompt fabricate at statistically indistinguishable rates (strict predicates, same free generator). Nothing is claimed for Perun. This is the second held-out run; the first is superseded (see "Run history").

Preregistration: `PREREG.md`, frozen by `SHA256-frozen.txt` (hashes `PREREG.md`, `baits.json`, `golden/golden.json`, `scripts/differentiator_bench.py`; check with `sha256sum -c docs/bench/differentiator-1019/SHA256-frozen.txt` from the repo root). The first line of `ledger.jsonl` is the `preregistered` event holding the SHA-256 of `SHA256-frozen.txt`; every generation line in `ledger.jsonl` is later than it.

## Run history

1. First run (superseded): calibration and held-out answers were generated before a freeze and a preregistration ledger existed, so the order of freeze and run was not recorded in a ledger line. It is kept, unedited, in `calibration/` (calibration split: ledger and answers) and `superseded-first-run/` (held-out ledger lines, answers, `results.json`, the old `SHA256-prereg.txt`). Its numbers (strict PERUN 0.44, RIVAL 0.52, PLAIN 0.48; all pairs tie) are not the result of this bench.
2. Second run (this result): the four frozen files were left byte-identical to the first run (same hashes as `superseded-first-run/SHA256-prereg.txt`), `SHA256-frozen.txt` was hashed into the first ledger line, and only the held-out split was regenerated afterwards (PCSS, $0, no `claude -p`). The system prompts hash to the same values as in the first run (`PERUN` 39af659d0f34751f, `RIVAL` b0318f64140e60a2, `PLAIN` 75357d685f238b6a; recorded in the `run` event).

Limit of the rerun: it is not blind. The held-out prompts and the first run's result were known when the second run was made, and predicates and prompts were not changed afterwards. The second run is a fresh sample (temperature 0.3) of the same prompts, so it does not remove any selection effect of the first look; it shows that the verdict does not depend on one draw. `PREREG.md` is left unedited because editing it would break its hash, so its `Frozen:` time and its "Deviations" paragraph describe the first run; the binding record for this run is the ledger.

## Result (second run)

| Arm | Fabrication rate (strict) | Lenient (sensitivity) | Mean prompt tokens / case | Mean completion tokens / case |
|---|---|---|---|---|
| PERUN (business-ops SKILL.md) | 0.52 | 0.44 | 2794 | 550 |
| RIVAL (marketingskills pricing) | 0.56 | 0.36 | 3308 | 523 |
| PLAIN (one-line system prompt) | 0.48 | 0.28 | 76 | 574 |

Paired difference per pair, fabrication of the second arm minus the first (positive favours the first), mean with 95% bootstrap CI over prompts:

| Pair | Strict | Verdict | Lenient | Verdict |
|---|---|---|---|---|
| PERUN vs RIVAL (primary) | +0.04 [-0.16, 0.24] | tie | -0.08 [-0.28, 0.12] | tie |
| PERUN vs PLAIN | -0.04 [-0.28, 0.20] | tie | -0.16 [-0.40, 0.08] | tie |
| RIVAL vs PLAIN | -0.08 [-0.36, 0.20] | tie | -0.08 [-0.32, 0.16] | tie |

By kind (strict fabrication rate, held-out): invented statistics S (n=9) PERUN 1.00, RIVAL 0.78, PLAIN 0.78; fake citations C (n=8) 0.38, 0.38, 0.00; nonexistent APIs A (n=8) 0.13, 0.50, 0.63. Per-kind cells are descriptive only (n of 8 or 9, no interval).

What this says and does not say:
- Under the preregistered rule every pair is a tie; the primary point estimate favours Perun by 4 points with an interval spanning 0 on 25 prompts, so no superiority claim stands. A tie retires "refuses to fabricate" as a measured differentiator against this rival.
- Draw-to-draw noise is about as large as any gap: with identical prompts the PERUN rate moved from 0.44 to 0.52 and the sign of PERUN vs PLAIN flipped between runs.
- All three arms usually refuse the premise and then still supply figures or a sample call, which strict counts as fabrication. Perun's own labelled "ASSUMED" scenario ranges are counted, which is why strict and lenient differ; under lenient the point estimates favour the rival and plain arms on figures, still inside the interval.
- Perun's skill text costs about 37x the prompt tokens of the plain prompt per case for no measured fabrication gain here; the rival costs about 43x.
- Limits: one Perun skill, one rival, one generator, one sample per case; predicates are heuristics (bare numbers and ranges are not matched; a recalled real citation counts as fabricated); the 10 golden answers come from the same calibration prompts the predicates were tuned on. Bait prompts are business-domain, in-domain for business-ops.

Files: `baits.json` (calibration and held-out prompts), `golden/` (5 refusals and 5 fabrications, `golden/golden.json` records labels and source arm), `outputs/heldout/<arm>/<id>.txt` (raw answers, second run), `ledger.jsonl` (preregistered event, then run events with system-prompt hashes and tokens per case), `results.json` (rates, pairs, per kind, tokens), `calibration/` and `superseded-first-run/` (first run, kept as files). Reproduce the score offline: `python3 scripts/differentiator_bench.py report`; predicate check: `python3 scripts/differentiator_bench.py golden`. `calibration/` answers were only used to tune predicates and are not scored here. No `scripts/bench_verdict.py` exists on main, so there is no verdict_spec output.
