Business-ops "lead with the call" against its strongest public rival (marketingskills pricing), round 5, 2026-10-17. Preregistration: PREREGISTERED.md (hashes in SHA256-frozen.txt, SHA256-scenarios.txt, SHA256-selection.txt, all written before the step they freeze). All calls on the PCSS endpoint, $0. Rival text is MIT, notice in LICENSE.rival.txt.

Result: reverted. The business-ops SKILL.md and evals are unchanged; nothing ships except this bench.

Held-out, n=60 fresh fictional scenarios (disjoint from every earlier set, `bench.py check` clean, about half legal, tax, accounting or regulatory questions), generator Qwen3.5-397B-A17B, judge v2 of scripts/rival_eval.py (neutral labels, reason-first, cascade GLM-5.1 then GLM-5.2 then gpt-oss_120b; GLM-5.1 slot-1 rate 0.508 so it scored both arms), both orders, strict agreement else 0.5, rival generated once and shared, bootstrap 10,000 resamples seed 1:
  v0 (unedited)        0.508 [0.392, 0.625]   26 wins / 9 ties / 25 losses
  e (selected on tune) 0.592 [0.483, 0.700]   29 / 13 / 18
  paired (e - v0)      +0.083 [-0.025, 0.183]
Keep rule (paired CI lower bound above 0): failed (-0.025). Superiority rule (win-rate CI lower bound above 0.5): failed (0.483).

Tune (n=10, selection only): v0 0.55, c 0.65, d 0.70, e 0.75; e won the preregistered rule. e is round 4's restructure c reworded to the owner decision (call first, general rule plus computed figures for legal, tax and accounting, one-sentence closing disclaimer, routing note only for jurisdiction-specific or high-stakes items).

Reading: the direction is positive (+0.083; e scored higher than v0 on 12 scenarios, lower on 6, equal on 42; only the interval is the verdict) and v0 itself moved from 0.312 (round 4, three-judge panel, 40 scenarios) to 0.508 here, so the panel, the judge v2 harness and the scenario mix matter as much as the edit. The edit is neither shipped nor ruled out; a larger fresh set under a new preregistration is the way to resolve an interval this wide.

Files: mkvariants.py builds prompts/perun_business-ops_{v0,c,d,e}.txt from the frozen base; bench.py runs seeds, scenarios, check, run, paired; results/ holds per-arm and paired records; outputs/ and judge/ hold every generated answer and judge verdict.

Redaction note: the writer used one first name that the repository's local privacy banlist matches (a common given name, fictional here). After the run, that single token was replaced with another fictional first name in the three files that contain it (scenarios/business-ops-heldout.json, outputs/e/h01.txt, outputs/v0/h01.txt) so the privacy gate passes. SHA256-scenarios.txt is the pre-redaction freeze and so no longer matches the heldout file byte for byte; no scores or verdicts were recomputed or changed.
