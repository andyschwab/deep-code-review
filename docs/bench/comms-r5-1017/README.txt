communication-structure round 5 against humanizer, 2026-10-17: decision-brief mode. Cost: $0 (free PCSS models only; no claude -p).

BLUF
- REVERT. The preregistered keep rule needed the paired difference (edit minus unedited skill) to have a 95% bootstrap CI lower bound above 0 on 60 fresh held-out scenarios. The selected edit E2 (the digest stays the default; a labelled decision-brief mode is added for messages that ask the reader to decide) scored a paired difference of -0.025, 95% CI [-0.117, +0.067], under the primary judge GLM-5.1. No SKILL.md, reference or eval edit ships; only this bench.
- Superiority over humanizer is not shown: E2 vs the rival 0.358, 95% CI [0.258, 0.467] (unedited skill 0.383 [0.283, 0.483]); the bar was a lower bound above 0.5.
- Descriptive and not a keep criterion: on the 33 decision-asking held-out scenarios (ask + report tags) the paired difference was -0.106, on the 27 without a decision (status + diff) +0.074. The second group saw the same digest rules in both arms, so +0.074 is a sample of the noise at n=27; the first is the group the mode targeted and it did not improve. The other two judges (sensitivity only): GLM-5.2 +0.025 [-0.075, +0.125], gpt-oss_120b -0.083 [-0.200, +0.033]. All three intervals contain 0.

Setup (PREREGISTERED.md and SHA256-frozen.txt written before any scenario, seed or arm generation; SHA256-selected.txt before the held-out scenarios were written; SHA256-held.txt before any held-out arm was generated)
- Arms: V0 (unedited skill), E1 (compact brief-mode section), E2 (labelled brief skeleton), E3 (E1 plus one worked example); prompts/ holds each full system prompt, mk_arms.py builds them from SKILL.md at base commit 3d9a30ff. Rival: humanizer v3.1.0 (prompts/RIVAL.txt, MIT, LICENSE.rival.txt), generated once per scenario.
- Harness: scripts/rival_eval.py judge v2 (blind, no rubric, random labels, both orders, strict agreement else 0.5; cascade GLM-5.1, GLM-5.2, gpt-oss_120b by slot-1 health, pooled over every arm so a paired comparison shares one judge). Generator Qwen3.5-397B-A17B, never a judge. bench5.py imports the harness functions and caches every output and verdict; nothing is overwritten.
- Tune (n=10; 4 ask, 3 status, 2 diff, 1 report), primary judge GLM-5.2 (GLM-5.1 slot-1 rate 0.387 was out of band): win rate vs rival E1 0.40, E2 0.50, E3 0.30, V0 0.40. E2 selected by the highest-win-rate rule (all within noise at n=10; tune_report.txt).
- Held-out (n=60; 24 ask, 18 status, 9 diff, 9 report), fresh seeds excluded against every earlier seed file; max word-trigram Jaccard 0.067 against 440 earlier scenarios and this round's tune set (overlap_held.txt). Primary judge GLM-5.1 (slot-1 rate 0.419, in band). held_report.txt has every number; per_scenario_held.json has the per-scenario scores.

Descriptive guardrails (held_report.txt)
- Mean words: V0 188.9, E2 218.7, rival 224.4. E2 reached length parity with the rival and still did not gain.
- Mean numeric tokens in an answer that are absent from the scenario (fabrication proxy): V0 0.65, E2 0.73, rival 1.73. The edit did not raise it materially.

Deviations
- bench5.py seeds() was changed once, before any held-out scenario or arm existed (SHA256-amend.txt): the first held seed call returned wrong tag counts, so it now asks per tag, keeps the first k seeds, and gives the writer only old topics (old tags made it copy them). The tune seeds were made by the frozen version.

Limits: one generator family, judges not Claude, scenarios written by a model, regex-level fabrication proxy, the skill is written for Claude. The held-out result is evidence for this host and judge set only. The round-4 diagnosis (../comms-r4-1017/DIAGNOSIS.md) remains a hypothesis: this round did not confirm that adding a decision-brief mode closes the gap on these judges.

Reproduce: from the repo root, with PCSS_KEY in the environment, `cd docs/bench/comms-r5-1017 && python3 mk_arms.py` (refuses to overwrite), then `SPLIT=held python3 bench5.py report E2 --base V0` replays the cached verdicts offline.
