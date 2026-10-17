communication-structure round 3 against humanizer, 2026-10-17. Cost: $0 (free PCSS models only; ledger.jsonl has every call's token usage, including refused calls).

BLUF
- REVERT. The selected candidate (C2) scored 0.325, 95% CI [0.225, 0.438], majority of 3 judges, n=40 fresh held-out scenarios. The preregistered bar is a lower bound above 0.5 and a point estimate at least the unedited skill's, so it fails the first condition (it meets the second: the unedited skill scored 0.212 [0.125, 0.300] on the same set). No SKILL.md, template or eval edit is committed; only this bench ships.
- Per judge, C2 vs RIVAL: DeepSeek-V4-Flash 0.412 [0.300, 0.525], GLM-5.2 0.312 [0.188, 0.438], gpt-oss_120b 0.325 [0.200, 0.450]. No judge puts the lower bound above 0.5.
- Neither version beats humanizer on this host. The edit's own share over the unedited skill is about +0.11 (0.325 vs 0.212), with overlapping intervals.

What changed versus round 2 (all in PREREGISTERED.md)
- Candidates from the judge reasons of 196 verdicts where the rival won: C1 (no trailing notes or skill vocabulary in the artifact), C2 (C1 plus a `pr` template with no forced Why / Risk and rollback lines, a plain title, Testing and Open questions sections), C3 (C2 plus a decision template that keeps each option's cost, time and risk, 300-word budget), C4 (C2 plus no sign-off placeholder and a stated recommendation). C0 is the round-2 edit, reference only.
- Tune split: fresh 10 scenarios (tune_report.txt). Majority win rate vs RIVAL: BASE 0.20, C1 0.30, C2 0.35, C3 0.25, C4 0.35 (C4 was added after the first three, see Amendment 1 in PREREGISTERED.md). C2 and C4 tied; the preregistered tiebreak (smaller edit) picked C2. All within noise at n=10.
- Held-out: fresh 40 scenarios, 3 judges (DeepSeek-V4-Flash, GLM-5.2 non-thinking, gpt-oss_120b), both orders, strict agreement per judge, majority across judges; rival generated once per scenario. overlap.txt: the highest word-trigram Jaccard of any new scenario against 240 earlier scenarios is 0.03.

Held-out results (held_report.txt)
- C2 vs RIVAL, majority: 0.325 [0.225, 0.438]; 5 clear wins, 19 clear losses, 16 splits. FAIL.
- BASE vs RIVAL, majority: 0.212 [0.125, 0.300]; 2 clear wins, 25 clear losses, 13 splits.
- Slot-1 rate (share of verdicts that picked Response 1, no ties): DeepSeek-V4-Flash 0.650, GLM-5.2 0.581, gpt-oss_120b 0.487 over 160 verdicts each. Both-order strict scoring cancels this.
- Post hoc, descriptive only (chosen after seeing the results): by type, majority win rate C2 vs BASE: 16 status notes 0.312 vs 0.062; 12 PR bodies 0.333 vs 0.458; 12 executive summaries 0.333 vs 0.167. The email form and the no-meta-note rule helped notes again. The C2 `pr` template did not help PR bodies; it scored below the unedited skill there, so the PR-body change is not supported by this set.

Caveats
Non-Claude generator and judges; both skills were written against Claude, so this result does not transfer to Claude in either direction. n=40, one scenario set, sampling not seeded, no lint-and-rewrite loop. Four candidates were compared on 10 tune scenarios, so the selection is noisy. The candidates were derived from round-2 verdicts on different scenarios, scored by the same judge families. GLM-5.2 ran in non-thinking mode (round 2 used thinking mode), so its numbers are not comparable to round 2's. ledger.jsonl holds 120 refused calls (HTTP 403 from the sandbox proxy, no cost, no verdict) from one detached run that lost its network permission; every verdict in the results comes from a later complete run.
