# Round 7 preregistration: idea-critic c6 against v0, n=100 fresh held-out (written 2026-10-17, before any round-7 generation or judging)

Scope: the `idea-critic` skill only; PCSS models only (host llm.hpc.psnc.pl); no paid call. Earlier rounds measured v0 at 0.575 (round 5, n=40) and 0.475 (round 6, n=40) against the rival, and the candidate c6 at 0.550 (round 6, n=40, `../idea-critic-r6-1017/`). Those n=40 sets cannot resolve a difference of this size, so this round draws 100 fresh scenarios and tests the paired difference.

## 1. Arms (all three answer each scenario once; same generator, same task wrapper)
- `rival`: the vendored rival prompt `../exec-1017/prompts/rival_idea-critic.txt`, reused unchanged. Answers are generated once and frozen in `RIVAL-sha256-r7.json` before any other arm; `run` refuses to start if they change.
- `v0`: `prompts/perun_idea-critic_v0.txt`, a byte copy of `.claude/skills/idea-critic/SKILL.md` on origin/main at this commit.
- `c6`: `prompts/perun_idea-critic_c6.txt`, byte copy of round 6's candidate (step 6 only: bounded first step, numeric tripwire at a dated checkpoint, figure error first).

## 2. Scenarios
100 fresh fictional scenarios, ids `r7-001`..`r7-100` (a namespace no earlier round uses), `scenarios7/idea-critic-r7.json`. Settings (`prompts/seeds7.txt`) are drawn from `gpt-oss_120b` (temperature 0.9) and kept only if the invented company name is absent from every file under `docs/bench/` outside this directory, from `scripts/eval-fixtures/` and from the idea-critic evals, and passes the privacy gate. Scenario text comes from the unchanged writer briefs (`../exec-1017/prompts/writer_*.txt`), 100-280 words, regenerated up to four times on a length or privacy miss. `bench7.py check` asserts disjointness from every earlier idea-critic round: ids, company names, exact texts and shared 10-word shingles; it must print `overlaps none` before any answer is generated. The seeds and scenario file are hashed in `SHA256-scenarios7.txt` before any answer exists.

## 3. Judging
Judge prompt v2 (`prompts/judge_v2.txt`, byte-identical to rounds 5 and 6). Judges GLM-5.1, GLM-5.2 and gpt-oss_120b, each in both orders (shuffled per scenario and judge); a judge's verdict counts only when both orders agree, else tie; the majority of three decides, else tie (0.5). Score 1 / 0.5 / 0. Generator Qwen3.5-397B-A17B never judges (no thinking, 3000 tokens, temperature 0.7). The `scripts/rival_eval.py` judge prompt is a different (label-based) variant; this round keeps round 5/6's v2 so the numbers stay comparable with them.

## 4. Decision rule (fixed now)
- Statistic: per-scenario score difference c6 minus v0 on the same 100 scenarios and the same frozen rival answers; paired bootstrap, 10,000 resamples of scenarios, seed 1, percentile 95% interval.
- Ship c6 into `SKILL.md` (with an eval) only if the paired lower bound is above 0. Otherwise `SKILL.md` is unchanged and only this bench ships.
- A claim that an arm beats the rival requires that arm's own win-rate lower bound above 0.5 (same bootstrap). Both arms' win rates with intervals are reported regardless, and so are wins/ties/losses and order disagreement.
- Analysis is run once on the full 100; no scenario is dropped, no arm regenerated after judging, no post hoc rule change. Incomplete judge records are re-run (never overwritten).
- Skeptic note, recorded: if c6's true effect is about +0.075 (round 6) with per-scenario sd near 0.6, the paired interval at n=100 has half-width about 0.12, so passing needs an effect larger than round 6 suggested; a miss is evidence the edit is not worth shipping, not a proof it does nothing. Kill criterion: no re-run of this rule on the same set.

## 5. Known weaknesses
Open models on one cluster; system-prompt-only arms; ties count 0.5; one run per arm; gpt-oss_120b writes seeds and scenarios and also judges; judge order disagreement near 0.3; scenario text is model-written; the c6 text was chosen by the round-6 tune, not this round.
