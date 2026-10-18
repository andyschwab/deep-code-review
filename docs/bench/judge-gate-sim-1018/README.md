# Judge slot-1 bonus replay and simulation, 2026-10-18

BLUF: FAIL. The preregistered claim (a slot-1 bonus leaves the headline win rate and the paired difference unbiased, only widening the interval) is not supported. In the model the bonus shrinks scores toward 0.5: every scenario the judge would otherwise decide for sure (true preference near 0 or 1) loses part of its score, so a win rate above 0.5 reads low, one below 0.5 reads high, and a paired difference reads smaller than it is. Worst cell across both data sources: |bias| 0.0018 and coverage 0.939 at delta 0, 0.0269 and 0.899 at delta 0.2, 0.0545 and 0.657 at delta 0.4. The pass criterion (|bias| at most 0.01, coverage at least 0.93) holds up to delta 0.05 in the spent-verdict replay and up to delta 0.10 in the synthetic simulation; the largest delta where every cell passes is 0.05. The resolved share falls from 0.81 (replay) and 0.62 (synthetic) at delta 0 to 0.66 and 0.53 at delta 0.2, so the skew costs power as well. In the synthetic cells with a slot-1 share of 0.64 to 0.69 (delta 0.15 to 0.20, the observed 0.62 to 0.67 range) the worst bias is 0.011 to 0.020, and it falls on the paired difference. Offline, $0, no model calls. No skill, rival row or past verdict changes. Consequence for the Proposal in `docs/bench/judge-calib-1018/README.md`: item 4's claim ("unbiased in expectation, only the width changes") should be rewritten as "biased toward 0.5 by a bounded amount", and the sensitivity range in item 2 is the right tool for it.

## Preregistration

Written before `sim.py` was run. `SHA256-frozen.txt` and the "preregistered" event in `ledger.jsonl` hash `sim.py` and the two spent verdict files as they were when this section was written.

### Claim under test

Item 4 of the Proposal in `docs/bench/judge-calib-1018/README.md` (PR #1689, diagnosis item 5): a judge that adds a slot-1 bonus on top of its true preference leaves the headline win rate unbiased in expectation, and the paired difference between two arms unbiased, with only the interval width and the resolved share changing. Offline replay and simulation only: no model calls, $0.

### Judge model

Per scenario `i` the judge has a true preference `p_i`, the probability that it prefers Perun's answer with no position effect. With a slot-1 bonus `delta` (probability scale), in the order where Perun is shown first Perun is picked with probability `clip(p_i + delta)`, and in the order where the rival is shown first Perun is picked with probability `clip(p_i - delta)`, where `clip` limits to [0, 1]. The two orders are drawn independently and the judge never says "tie". Scoring is the frozen protocol of `scripts/rival_eval.py`: a scenario scores 1 or 0 only when both orders pick the same answer and 0.5 otherwise (a split counts 0.5). The headline win rate is the mean scenario score, the paired difference is the mean of `score(v1) - score(v0)` per scenario, and the intervals are 95 percent percentile bootstrap intervals of those means.

Grid: `delta` in 0.00, 0.05, ..., 0.40. Each cell uses 2000 repetitions, `n` = 150 scenarios, 1000 bootstrap draws per interval (resampling scenarios with replacement). The bootstrap resamples the multiset of score values, which is the same distribution as resampling scenarios.

### Data

1. Spent-verdict replay. For each round (growth round 4 and round 5), judge (GLM-5.1, GLM-5.2, gpt-oss_120b) and arm (v0, v1), `p_i` is the observed scenario score from `results/judge-verdicts.json` (mean of the two orders; a "tie" verdict counts 0.5). Each repetition draws 150 scenarios with replacement from the 150 spent ones (v0 and v1 are drawn jointly) and simulates the judge with `delta` on top. The truth is the mean of the spent `p_i` (and of `p_i(v1) - p_i(v0)` for the difference). Because the spent verdicts already carry each judge's own slot-1 pull, `delta` here is incremental.
2. Synthetic. `p_i` is Beta with mean `w` and concentration `kappa`, for `w` in 0.45, 0.50, 0.55, 0.60 (arm v1) and `kappa` in 2 (wide, many scenarios near 0 or 1) and 8 (concentrated). The v0 arm has `w` = 0.45 and the same `kappa`; v0 and v1 are drawn independently, so the true paired difference is `w - 0.45` (0, 0.05, 0.10, 0.15). The truth is `w` exactly (a superpopulation mean, so the estimate is unbiased at `delta` = 0 by construction).

### Reported per cell

Bias (mean estimate minus truth) and 95 percent interval coverage of the headline win rate (v0 and v1) and of the paired difference, the mean resolved share (scenarios where both orders pick the same answer), the mean slot-1 share of picks (to anchor `delta` to the observed 0.62 to 0.67), and the mean interval width.

### Pass criterion

A cell passes when |bias| is at most 0.01 and coverage is at least 0.93, for both headline win rates and for the paired difference. The claim passes at a `delta` only when every cell of both data sources passes there. The overall verdict is PASS only if the claim passes at every grid `delta` from 0.00 to 0.20 (the range that brackets the observed skew: a slot-1 share of 0.62 to 0.67 is `delta` of about 0.12 to 0.17 when `p_i` is near 0.5); values above 0.20 are stress points, reported but not part of the verdict. Otherwise the verdict is FAIL and the README states the largest `delta` below which every cell still passes. The criterion is not changed after the run.

### Not part of this test

No skill, rival row or past verdict changes. No claim about the real judges beyond the model: the model has no tie verdicts, draws the two orders independently, and uses a constant `delta`.

## Results

Frozen `sim.py` run once (`python3 docs/bench/judge-gate-sim-1018/sim.py run`, about 3 minutes on 14 cores, seeded per cell); `results/results.json` holds all 126 cells (54 replay, 72 synthetic) and `python3 sim.py selftest` checks the judge model against closed forms and the spent-verdict loader against the frozen `verdict.json` win rate. Verdict per the preregistered rule: **FAIL** (the claim does not pass at delta 0.10, 0.15 or 0.20). Largest delta where every cell passes: 0.05.

Worst case over all cells of a source (headline win rates of both arms and the paired difference). "Slot-1" is the mean share of decisive picks that chose Response 1; "resolved" is the share of scenarios where both orders pick the same answer.

| delta | replay max abs bias | replay min coverage | replay resolved | replay slot-1 | pass | synthetic max abs bias | synthetic min coverage | synthetic resolved | synthetic slot-1 | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 | 0.0016 | 0.939 | 0.814 | 0.500 | Y | 0.0018 | 0.939 | 0.616 | 0.500 | Y |
| 0.05 | 0.0079 | 0.941 | 0.781 | 0.534 | Y | 0.0021 | 0.934 | 0.610 | 0.549 | Y |
| 0.10 | 0.0148 | 0.929 | 0.744 | 0.569 | N | 0.0043 | 0.941 | 0.592 | 0.597 | Y |
| 0.15 | 0.0203 | 0.925 | 0.704 | 0.603 | N | 0.0108 | 0.935 | 0.564 | 0.644 | N |
| 0.20 | 0.0269 | 0.899 | 0.659 | 0.637 | N | 0.0195 | 0.922 | 0.525 | 0.689 | N |
| 0.25 | 0.0340 | 0.869 | 0.610 | 0.672 | N | 0.0275 | 0.901 | 0.479 | 0.731 | N |
| 0.30 | 0.0410 | 0.821 | 0.558 | 0.706 | N | 0.0356 | 0.866 | 0.426 | 0.771 | N |
| 0.35 | 0.0463 | 0.763 | 0.504 | 0.740 | N | 0.0454 | 0.762 | 0.369 | 0.809 | N |
| 0.40 | 0.0542 | 0.664 | 0.444 | 0.774 | N | 0.0545 | 0.657 | 0.309 | 0.843 | N |

Reading it:

- Mechanism. The bonus only moves a score when the clip at 0 or 1 binds. A scenario with `p` between `delta` and `1 - delta` keeps its expected score exactly; one with `p` near 1 loses up to `delta / 2` and one near 0 gains up to `delta / 2`. Bias therefore grows with delta and with the share of near-certain scenarios, and always points toward 0.5. The concentrated synthetic setting (`kappa` 8) is milder than the wide one (`kappa` 2, `w` 0.60: headline bias -0.0130 and paired-difference bias -0.0195 at delta 0.2, versus -0.0027 and -0.0044).
- Paired difference. It is the most exposed statistic: its truth is small and the shrinkage applies to both arms, so the relative bias is largest there (replay round 4, GLM-5.2: true diff 0.138, bias -0.0269 at delta 0.2, coverage 0.900). A shrunk difference mostly makes a real win harder to see, not a null easier to fake; the null cell (`w` = 0.45, true diff 0) stays unbiased across the whole grid (|bias| at most 0.0023 for `kappa` 2 and 0.0013 for `kappa` 8, coverage at least 0.938), because both arms shrink by the same amount.
- Coverage. Percentile bootstrap coverage is 0.94 to 0.96 at delta 0 and falls only through the bias, so up to delta 0.2 the interval is slightly optimistic (0.90 to 0.95), not broken; it collapses above 0.3.
- Spent-verdict replay at delta 0 is a pure resample of the observed scenario scores and reproduces them (bias at most 0.0016). Its resolved share is high (0.79 to 0.85) because the observed score set is treated as a deterministic preference (0, 0.5 or 1), unlike the real 0.58 to 0.59 resolved share of round 5; read its resolved column as an upper bound, and the bias column as a bound for a judge that is otherwise perfectly consistent.

## Caveats

- The model is a stand-in: constant delta, independent draws per order, no tie verdicts, `p` observed from the already skewed verdicts (replay) or drawn from a Beta (synthetic). A judge whose skew concentrates on close pairs (the calibration finding) is closer to a delta that grows as `p` nears 0.5, where the clip does not bind and bias is smaller; this run does not model that.
- Delta is a probability-scale bonus. The mapping to the observed slot-1 share is approximate (slot-1 share is 0.5 plus delta when `p` is 0.5, less when `p` is near 0 or 1).
- 2000 repetitions give a bias standard error near 0.001 and a coverage standard error near 0.005; cells within those of the thresholds (for example replay round 4 GLM-5.2 at delta 0.10, coverage 0.929 on the paired difference) are borderline. The failures at delta 0.15 and above are not.
- Synthetic v0 and v1 are drawn independently, whereas the spent arms share scenarios; this lowers the paired-difference power in the synthetic cells but does not affect the bias.
- Verdict rule, grid and data are as preregistered above; nothing was changed after the run.
