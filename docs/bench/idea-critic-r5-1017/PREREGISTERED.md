# Round 5 preregistration: idea-critic against its rival (written 2026-10-17, before any round-5 generation or judging)

Scope: the `idea-critic` skill only; PCSS models only. Rounds 3 and 4 did not clear the bar (round 4: unedited v0 0.450, candidate 0.412; `../idea-critic-r4-1017/ERRATA.md`). Bar for this round: the 95% bootstrap lower bound is above 0.5 AND the edit's win rate is at least unedited v0's on the same held-out set. Otherwise the edit is reverted and only this bench ships.

## 1. Root cause, read from the round-4 judge records (`../idea-critic-r4-1017/judge4/idea-critic/PERUN_v0/`, 40 held-out scenarios, v0 against the rival)

Two separate problems.

A. Why the rival wins (13 scenarios where v0 lost, reasons of the judges that voted for the rival):
- the stop trigger: at least 8 of 13 reasons credit the rival's trigger as more specific, earlier or tighter (for example h10: an 8% margin floor and a 10-project monthly floor, where v0 repeated the requester's own 5% example; h15 and h33: a numeric floor at a dated checkpoint);
- a bounded first step (staged capital, pilot, soft launch): at least 5 of 13 (h10, h12, h31, h36, h03);
- a figure or logic error caught: at least 6 of 13 (hand count of the reason text, a lead not a proof) (h14, h15, h20, h22, h38, h03).
Round 4's `cA` bundled the first and second item and did not hold up (0.412), so this round tests only the trigger, which is the most frequent reason and the smallest change.

B. Why many votes are indistinguishable. Of 40 v0 scenarios, 18 ended as a tie, and no judge ever returned "tie" in both orders: every tie came from the two orders disagreeing (per judge, order disagreement was 14, 16 and 24 of 40; judge slot-1 rates 0.60 to 0.80). With strict both-order agreement, position bias turns a real preference into a 0.5 and shrinks the effective n to about 22 decided scenarios. The v1 judge prompt asks for a one-sentence reason after the verdict (no work before the verdict), which invites a first-slot pick. This is a fixture problem, not a skill problem.

## 2. Fixture fix (judge prompt only; scenarios, generator, rival, judges, protocol unchanged)

`prompts/judge_v2.txt` makes the judge work first (recompute the figures, say what each response catches or misses and how concrete its step and stop trigger are), tells it the order carries no information, and allows "tie" only when no decision-relevant difference is found. `prompts/judge_v1.txt` is round 4's judge prompt, unchanged.

Pilot (diagnostic only, no skill edit involved): the round-4 v0 and RIVAL answers on the round-4 held-out scenarios (copied, not regenerated), judged by this round's three judges with v1 and with v2. Adopt v2 for tune and held-out if and only if its order-disagreement rate (computed by `bench5.py report`) is lower than v1's on the same pairs. The win rate is not a selection criterion. If v2 is not lower, v1 is used. The decision is written to `PILOT-RESULT.md` before the tune run.

## 3. The one edit (`prompts/perun_idea-critic_c5.txt`; diff against `perun_idea-critic_v0.txt`, the current `SKILL.md`, in step 6 only)

The kill-criteria clause reads "a leading, observable tripwire with a number, a date and the action when it fires; tighter than the requester's own example if theirs fires only after the money is spent" in place of "observable tripwire, date, action when it fires". One candidate, no variants.

## 4. Tune (n=10, selection only)

The old tune scenarios 01-10 (`../exec-1017/scenarios/idea-critic.json`), RIVAL and v0 answers copied from round 4 (generated once there), the candidate generated once. Judges as in section 5 with the prompt chosen in section 2. If the candidate's tune win rate is below v0's the edit is not taken forward (reverted, bench ships). Otherwise it goes to held-out; the tune result is not used for anything else.

## 5. Held-out (run once)

- 40 fresh scenarios `scenarios5/idea-critic-h5.json` (h01-h40), written by `gpt-oss_120b` at temperature 0.9 from the unchanged writer briefs and the 40 new fictional settings in `prompts/seeds5.txt`, whose company names were grep-checked to be absent from the rest of `docs/bench/`. Regenerated up to four times if outside 100-280 words or if `scripts/ci-gates.sh privacy` (committed and local banlists) hits. Their sha256 is taken before any answer is generated.
- Each RIVAL answer (`../exec-1017/prompts/rival_idea-critic.txt`) is generated exactly once, before any arm, and its sha256 frozen in `RIVAL-sha256-h5.json`; `run` refuses to start if they change. Records are never overwritten: a judge record is written with exclusive create only when all six calls parsed.
- Arms: v0 and the candidate on the same scenarios. Generator Qwen3.5-397B-A17B (never a judge, no thinking, 3000 tokens, temperature 0.7).
- Judges GLM-5.1, GLM-5.2 and gpt-oss_120b (the last also wrote the scenarios; it judges answers, not scenarios), each in both orders; a judge's verdict counts only when both orders agree, else tie; the majority of three decides, else tie (0.5).
- Score 1 / 0.5 / 0 per scenario; bootstrap 10,000 resamples, seed 1, percentile. Slot-1 rate and order disagreement per judge are reported.
- Known weaknesses: open models on one cluster; system-prompt-only arms (no references, tools, scripts); ties count 0.5; one run per arm; the judge prompt is changed from round 4, so round-4 numbers are not comparable to this round's; the tune set is small; gpt-oss_120b reasoning and GLM thinking-off settings differ.
