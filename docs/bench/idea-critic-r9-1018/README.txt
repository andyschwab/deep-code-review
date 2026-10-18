idea-critic, round 9 (branch bench/idea-critic-r7-1018): one frozen SKILL.md edit, n=150 fresh held-out, 2026-10-18. The directory is named r9 because r7 and r8 already exist (idea-critic-r7-1017, idea-critic-r8-1018).

Result: the edit (c9c) is shipped. Rule (PREREGISTERED.md section 3): ship iff the paired edit-minus-previous 95% bootstrap lower bound is above 0; win iff edit against the rival has a lower bound above 0.5. Both pass.
  held-out n=150 (scenarios9-held.json, ids r9-001..r9-150), rival gstack plan-ceo-review answers frozen in RIVAL-sha256-held.json, judges GLM-5.1 + GLM-5.2 + gpt-oss_120b, both orders, strict agreement else tie, majority of three, ties 0.5, bootstrap 10,000 resamples seed 1:
  previous text (v0): 0.470 [0.407, 0.533], 42 W / 57 T / 51 L (results9-v0-held-v2.json)
  edit (c9c):         0.570 [0.510, 0.630], 55 W / 61 T / 34 L (results9-c9c-held-v2.json)
  paired c9c minus v0: +0.100 [0.0333, 0.1633] (results9-paired-c9c-held.json); ship true, superior_to_rival true.

Method: losses.py clusters the judge reasons of v0 losses in rounds 5 to 8 (losses.txt). Three candidates (mkcands.py): c9a step 5 (recompute and open with the mismatch), c9b step 6 (capped first step, numeric dated kill metric with a named action), c9c both. Tune on the spent round-5 and round-6 held-out sets (n=80, their frozen rival answers and existing v0 judge records; calls in ledger-tune.jsonl, files in tune/): v0 0.525, c9b -0.0125, c9a -0.0125, c9c +0.0813 [-0.0125, 0.175] paired. The selection rule (TUNE_ORDER in bench9.py, written before the tune runs) took the most frequent loss cluster first and the first candidate with paired >= 0, which was c9c. PREREGISTERED.md and SHA256-frozen.txt were written before any held-out seed, scenario or judge call; the first line of ledger.jsonl is the timestamped preregistered event, the second is scenarios_frozen (SHA256-scenarios.txt). Driver bench9.py (derived from ../idea-critic-r8-1018/bench8.py; reuses ../exec-1017/bench.py); judge prompt v2 byte-identical to rounds 5 to 8. PCSS only, no paid call, no claude -p, no key printed, fictional data only.

Held-out disjointness: ids, company names and exact texts are not in any other docs/bench text; 6-word shingle overlap of every scenario with all docs/bench text outside this directory, the eval fixtures and the idea-critic evals is at most 0.10 unrounded (max 0.1000), at most 0.0691 inside the batch (bench9.py check); scripts/bench_check.py passes. Scenarios were rejection-sampled for overlap (scen: seven redraw rounds), so the set is somewhat less template-like than earlier rounds.

Caveats: open models on one cluster; system-prompt-only arms; one run per arm; the margin over 0.5 is 0.010; the edit was picked from three on a tune set of 80 spent scenarios (tune paired interval includes 0), so the held-out result is one fresh look and should be confirmed on a second fresh set; gpt-oss_120b writes seeds and scenarios and also judges; ties are 57 and 61 of 150; scenarios are model-written with more varied phrasing than rounds 5 to 8, so the rates are not strictly comparable with them; the edit text was written after reading earlier judge reasons; the rival answers were generated once under the same generator settings as the arms.

Disclosures:
- A first tune attempt ran with the sandbox blocking the PCSS host: 960 failed calls (no successful call, no output) were deleted before the real tune run; no tune scenario had been judged.
- Three judge records (c9c r5-h37 in tune, v0 r9-005 and c9c r9-134 in held-out) were incomplete after an unparsed reply and were completed by rerunning the driver; complete records are never overwritten.
- prompts/perun_idea-critic_v0.txt is the SKILL.md at origin/main when the round started (version stamp 1.593.0); the shipped file equals prompts/perun_idea-critic_c9c.txt byte for byte.
- The tune baseline for v0 is the single v0 sample already judged in rounds 5 and 6 (identical text apart from the version stamp).
- Disjointness was checked against the bench corpus at freeze time. Against the later main (after bizops-r4-1018 landed), held-out
  scenario r9-080 shares 19 of 183 6-word shingles (0.104) with one bizops-r4-1018 model output; the overlap comes from text written
  after the freeze, so it cannot have leaked into this run.
