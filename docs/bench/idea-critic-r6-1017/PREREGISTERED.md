# Round 6 preregistration: idea-critic against its rival (written 2026-10-17, before any round-6 generation or judging)

Scope: the `idea-critic` skill only; PCSS models only. Round 5 (`../idea-critic-r5-1017`) measured unedited v0 at 0.575 [0.450, 0.700] against the rival under judge prompt v2 (17 wins, 12 ties, 11 losses over 40 held-out scenarios) and reverted its edit (c5 below v0 on tune). Bar for this round: the edit's 95% bootstrap lower bound is above 0.5 AND its win rate is at least v0's on the same fresh held-out set. Otherwise the edit is reverted and only this bench ships.

## 1. Target causes (from round 5 README and PREREGISTERED section 1, hand counts over the round-4 judge reasons)
The rival wins on (a) a sharper, earlier stop trigger, (b) a bounded first step (staged capital, pilot), (c) a caught error in a given figure. Round 5's c5 touched only (a) and lost on tune by one scenario; round 4's cA bundled (a) and (b) with different wording. This round makes one edit that touches all three in step 6 only.

## 2. The one edit (`prompts/perun_idea-critic_c6.txt`; diff against `perun_idea-critic_v0.txt`, the current `SKILL.md`, step 6 only)
The decision "starts with the smallest bounded first step (a capped pilot or staged spend)"; the kill criteria become "a numeric floor or ceiling checked at a dated checkpoint before the main money is spent, and the action when it fires"; and a closing sentence "Lead with any error found in the requester's own figures." One candidate, no variants.

## 3. Fixture (unchanged from round 5)
`bench6.py` is `../idea-critic-r5-1017/bench5.py` with paths renamed and `seed` changed to copy round-5 tune answers. Judge prompt `prompts/judge_v2.txt` is byte-identical to round 5's. Generator Qwen3.5-397B-A17B (never a judge, no thinking, 3000 tokens, temperature 0.7). Judges GLM-5.1, GLM-5.2 and gpt-oss_120b, each in both orders; a judge's verdict counts only when both orders agree, else tie; the majority of three decides, else tie (0.5). Score 1 / 0.5 / 0; bootstrap 10,000 resamples, seed 1, percentile.

## 4. Tune (n=10, selection only)
Old tune scenarios 01-10, RIVAL and v0 answers and v0 judge records copied from round 5 (generated and judged once there, same judges and prompt). c6 generated once and judged once. Rule: c6's tune win rate must be strictly above v0's (v0 = 0.75 in round 5, `../idea-critic-r5-1017/results5-v0-tune-v2.json`); otherwise c6 is reverted, nothing goes to held-out, and the bench ships. The tune result is used for nothing else.

## 5. Held-out (run once, only if c6 beats v0 on tune)
- 40 fresh scenarios `scenarios6/idea-critic-h6.json` (h01-h40), written by `gpt-oss_120b` at temperature 0.9 from the unchanged writer briefs and the 40 new fictional settings in `prompts/seeds6.txt`. Every company name was grep-checked to be absent from the rest of `docs/bench/` (rounds 3-5 and all other suites). Regenerated up to four times if outside 100-280 words or if the privacy gate hits. sha256 of the scenario file is recorded in `SHA256-scenarios6.txt` before any answer is generated.
- Each RIVAL answer (`../exec-1017/prompts/rival_idea-critic.txt`) is generated exactly once, before any arm, and frozen in `RIVAL-sha256-h6.json`; `run` refuses to start if they change. Records are never overwritten.
- Arms: v0 and c6 on the same scenarios, same RIVAL answers, same judge prompt.
- Keep rule: c6 lower CI bound above 0.5 AND c6 win rate at least v0's win rate on this held-out set. Both met: SKILL.md step 6 takes the edit, with a `changelog.d` fragment. Otherwise revert and ship the bench only.
- Known weaknesses: open models on one cluster; system-prompt-only arms; ties count 0.5; one run per arm; tune n=10 is a weak selector and v0's tune 0.75 is a high bar; gpt-oss_120b writes the scenarios and also judges; judge-order disagreement remains around 0.3; the three target causes are hand counts, leads not proofs.
