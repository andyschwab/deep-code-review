# Preregistration: positioning and business-ops against their strongest rival, round 3 (2026-10-17)

Written and hashed (SHA256-frozen.txt) before any scenario, tune or held-out generation, or any judge call. Every model call goes to the PCSS endpoint ($0); no `claude -p`, no paid API.

## Baseline (existing evidence, read before this file was written)

- `docs/bench/rival-eval-baseline-1017` (frozen held-out n=10, judge DeepSeek-V4-Flash): positioning 0.500 [0.250, 0.750] against deanpeters positioning-statement; business-ops 0.400 [0.150, 0.700] against marketingskills pricing.
- `docs/bench/exec-1017` round 2 (held-out n=20, three judges, both orders): positioning v0 0.475 [0.325, 0.650]; business-ops v0 0.475 [0.300, 0.625]. Four earlier edit rounds were reverted there.

## Root cause (read from the judge reasons that favour the rival: exec-1017 judge4 v0 losses and the rival-eval-baseline losses)

Both skills lose for the same reason in two different scenario formats. The reasons name the rival as "decisive", "directly actionable", "ready-to-use", "client-ready", "concrete", and Perun as "a cautious hypothesis with validation caveats", "abstract", "evasive", "leaves decisions open", "unnecessary legal disclaimer", "diverts to legal disclaimers". The guardrails (positioning: every output is a hypothesis; business-ops: apply, never direct; route, never conclude; disclaimer up front) are read by the generator as an instruction to hedge, so the deliverable is a menu plus caveats, and a legal or trademark routing line appears even when not asked. Two secondary reasons recur: Perun does not reconcile the requester's own figures (positioning pilot revenue that cannot follow from the stated price and volume; business-ops stated churn against the observed revenue decline, a one-time versus recurring cost), and its stop metric is not tied to the requester's numbers.

## Candidates (smallest SKILL.md edit each; exact text in `mkvariants.py`, built into `prompts/perun_<skill>_{a,b,c}.txt`)

- positioning a: new section "Deliver the call, not a menu" (commit to one segment and lead message, answer each named alternative, say hypothesis once, route trademark/legal/market-size only when asked or claimed). b: new section "Check the user's numbers first" (reconcile figures, name the mismatch, thresholds computed from the user's figures with a date). c: a and b.
- business-ops a: disclaimer moved from "up front" to one closing line; new Lane A bullet "Commit when asked to choose between the user's own options" (apply-don't-direct still bars setting a price or spend from nothing; reconcile stated churn against the revenue trend; one-time versus recurring, sunk versus marginal). b: new Lane R bullet "Route with substance, not a bare referral" (name the condition under which the regime applies, obligations, the trigger for hiring counsel, questions to bring; still never conclude "you are" or "you are not" covered). c: a and b.
- v0 for each skill is the unedited `.claude/skills/<skill>/SKILL.md` at base commit d3ce8350 (`prompts/perun_<skill>_v0.txt`).

## Scenarios

Fresh and disjoint. Fifty one-line settings per skill were drawn once by Qwen3.5-397B-A17B (`prompts/seeds_<skill>.txt`, hashed here). Seeds 01-10 give the tune split (n=10, ids t01-t10); seeds 11-50 give the held-out split (n=40, ids h01-h40). Scenarios are written by the same blind writer (Qwen, temperature 0.7, 10 per call) from the standing harness briefs `scripts/eval-fixtures/rival/<skill>/brief.txt` (public purpose only; no skill or rival text); fictional companies and people only; used unedited, none dropped. Before any run they are checked disjoint from every earlier scenario set for the skill (the harness tune, heldout and heldout30 files and the exec-1017 scenario files): no 6-word-shingle overlap above 0.3, no identical prompt.

## Arms, judges, scoring

- Generator for every arm: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, the harness `GEN_TASK` wrapper, system prompt = the arm's text. The rival text is the one in the harness `rival.json` (positioning: deanpeters positioning-statement SKILL.md, sha256 44d46a65fa95871cf978f6863650c95be92f135f635f0197866344087b374909; business-ops: marketingskills pricing SKILL.md, sha256 b0318f64140e60a28d0cf71b1a6bf2aa214b96ef2bc3253c60d16ae480367d25; both equal the hashes recorded in the baseline). Each rival answer is generated once per scenario and shared by every Perun arm.
- Judges: DeepSeek-V4-Flash, GLM-5.2 (thinking off), MiniMax-M2.5; the harness rubric-free blind prompt; each judge sees every pair in both orders (order seeded by skill, arm, scenario, judge). A judge's vote counts for an arm only when both orders agree on that arm, else it is a tie; the majority of the three decides (two votes for one arm), anything else is a tie worth 0.5. The generator and the scenario writer are never judges. Per-judge numbers and slot-1 rates are reported as sensitivity and bias checks, never as the verdict.
- Score per scenario: 1 arm wins, 0.5 tie, 0 rival wins. CI = percentile bootstrap, 10,000 resamples, seed 1, over scenarios.

## Procedure

1. Tune (n=10): run v0, a, b, c against the rival. Selection only; no tune number is a verdict.
2. Selection: the candidate with the highest tune win rate; ties go to the smaller added text, then the earlier letter. It is run on held-out even if it does not beat v0 on tune (the run costs $0). The choice is frozen in `SHA256-selection.txt` (a hash of the tune results) before any held-out scenario is written.
3. Held-out (n=40): write the 40 scenarios, then run v0 and the selected candidate once each, against the same rival answers. No re-runs, no judge swaps, no scenario edits after seeing a result.
4. Keep rule, per skill: keep the edit only if the selected candidate's held-out win rate has a 95% CI lower bound above 0.5 AND its win rate is at least v0's on the same held-out set. Otherwise revert the SKILL.md edit (and its eval and changelog text) and ship the bench only.

## Caveats declared in advance

Generator, writer and judges are open models on one cluster, not the models users run. Both arms are system-prompt only: the Perun arm sees SKILL.md without its references or scripts, and the rival without its own. Sampling is not seeded, so a re-run differs; the earlier rounds moved by about 0.1 on re-judging. Best-of-three on n=10 overfits, which is why selection and verdict are on different sets. The scenario writer does not plant flaws in these briefs, so the "check the user's numbers" candidates are tested only on whatever inconsistencies the writer happens to produce.
