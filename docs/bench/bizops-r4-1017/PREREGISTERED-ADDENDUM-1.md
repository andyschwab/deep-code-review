# Addendum 1 (written after the tune results of v0, a, b, c were seen; before any held-out scenario was used, any held-out arm generated, or any held-out judge call)

Tune (n=10, selection only): v0 0.50, a 0.55, b 0.65, c 0.50. Reading the b outputs against the preregistered root cause: b changes content (Lane R answers the general rule) but still opens with the standing disclaimer in 7 of 10 answers and prints lane labels in 7 of 10, because it leaves the format rules alone; a and c remove both. The two fixes address different rows of the behavior table and are not in conflict, so one more candidate is added before selection:

- d: a and b applied together (`cand_d` in `mkvariants.py`, `prompts/perun_business-ops_d.txt`). The a, b, c and v0 prompt files are byte-identical to the frozen ones (hashes in SHA256-frozen-addendum-1.txt).

Selection now runs over a, b, c, d on tune by the same rule (highest tune win rate; ties to the smaller SKILL.md, then the earlier letter). d's tune run is the only new tune run. Held-out is unchanged: v0 and the single selected candidate, once each, same rival answers, same keep rule. Four candidates on n=10 inflate the tune number of the winner, which is why the held-out set alone decides and why a tune score is never reported as a result.

## Selection (frozen before any held-out arm generation)

Tune results: v0 0.50, a 0.55, b 0.65, c 0.50, d 0.60. By the rule, **b** is selected (highest tune win rate; no tie). It runs on held-out with v0. The hash of the tune results is in SHA256-selection.txt.
