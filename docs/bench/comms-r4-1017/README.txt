communication-structure round 4 against humanizer, 2026-10-17. Cost: $0 (free PCSS models only; ledger.jsonl has every call's token usage, 1,040 calls, 0 errors).

BLUF
- REVERT. The tune-selected candidate C (full-length worked examples per artifact kind, no 150-word default) scored 0.388, 95% CI [0.275, 0.512], majority of 3 judges, n=40 fresh held-out scenarios. The preregistered bar is a lower bound above 0.5 AND a point estimate at least the unedited skill's. It meets the second (unedited skill, "v0": 0.225 [0.125, 0.338] on the same set) and fails the first. No SKILL.md, template or eval edit is committed; only this bench and DIAGNOSIS.md ship.
- Post hoc and descriptive: paired C minus unedited skill = +0.163, bootstrap 95% [+0.037, +0.287] (analyze.py). A structural edit moves the skill about +0.16, more than the +0.10 to +0.12 of the three wording rounds, but it is still below humanizer on this host.
- Length parity was reached (mean words: unedited skill 149, C 193, rival 195) and C still lost, so length was a real part of the gap but not all of it. Notes gained most (0.562 vs 0.250 for the unedited skill, 16 scenarios); PR bodies 0.208 vs 0.125 (12) and executive summaries 0.333 vs 0.292 (12) barely moved.

Diagnosis (DIAGNOSIS.md, reproduced by diagnose.py): the skill's output contract is a compressed digest (about 150 words, core value only, no recommendation or rationale, three findings) while blind judges prefer the complete decision brief the rival produces. 64% of rival-win reasons name completeness or a stated recommendation (keyword match; the recommendation theme also appears in 37% of our-win reasons); per-scenario our/rival length ratio correlates -0.39 to -0.67 with the rival's share of verdicts.

Setup (PREREGISTERED.md and SHA256-frozen.txt written before any scenario or arm generation; SHA256-selected.txt written after tune and before any held-out scenario)
- Candidates share S (round-3 C1 plus the C4 fixes) and differ in one structural lever: A decision-brief skeleton, B coverage invariant with no word cap, C worked examples. mk_arms.py builds them by exact replacement.
- Tune (10 fresh scenarios, tune_report.txt), majority win rate vs RIVAL: BASE 0.15, PLAIN (no skill, descriptive) 0.35, C1 0.30, A 0.25, B 0.40, C 0.45. C selected. All within noise at n=10. PLAIN scored above BASE on tune, a hint that the unedited skill costs against no skill; not tested on held-out, so not a finding.
- Held-out: 40 fresh scenarios written by DeepSeek-V4-Flash from fresh seeds (16 notes, 12 PR bodies, 12 executive summaries); max word-trigram Jaccard 0.028 against 340 earlier scenarios and this round's tune set (overlap.txt). Generator Qwen3.5-397B-A17B (never a judge). Judges GLM-5.1, GLM-5.2 (non-thinking), gpt-oss_120b, both orders, strict agreement per judge, majority across judges; the rival answer was generated once per scenario.

Held-out results (held_report.txt)
- C vs RIVAL, majority: 0.388 [0.275, 0.512]; 8 clear wins, 17 clear losses, 15 splits. FAIL.
- BASE vs RIVAL, majority: 0.225 [0.125, 0.338]; 4 clear wins, 26 clear losses, 10 splits.
- Per judge, C vs RIVAL: GLM-5.1 0.338 [0.225, 0.450], GLM-5.2 0.388 [0.263, 0.512], gpt-oss_120b 0.438 [0.312, 0.562]. No judge puts the lower bound above 0.5.
- Slot-1 rate: GLM-5.1 0.562, GLM-5.2 0.600, gpt-oss_120b 0.519 over 160 verdicts each; both-order scoring cancels it.

Caveats
Non-Claude generator and judges; both skills were written against Claude, so this result does not transfer to Claude in either direction. n=40, one scenario set, sampling not seeded, no lint-and-rewrite loop, no tools for either arm. Three candidates were compared on 10 tune scenarios, so the selection is noisy. The by-type and paired numbers are post hoc. The worked examples in C teach the generator a fixed shape; a real user's source may differ. Amendment 1 (SHA256-amend.txt) is a driver fix after the freeze: overlap skips a split whose scenarios file is absent. One held-out scenario batch failed the writer's shape check once and was re-run before any arm was generated. The local origin/main ref could not be refreshed (the sandbox blocked the fetch), so the skill text is the one at the local origin/main, which equals round 3's BASE byte for byte.

Third-party text: prompts/RIVAL.txt is the humanizer skill (SKILL.md, MIT, Copyright (c) 2025 Siqi Chen), included unmodified; the license is in LICENSE.rival.txt.
