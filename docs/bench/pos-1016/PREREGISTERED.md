# Preregistration: product-output-safety held-out re-test (2026-10-16)

Frozen before the first call. File hashes are in `SHA256-frozen.txt`.

## Question

`docs/perun-vs-rivals.md` H1 scored product-output-safety 0.55 [0.400, 0.700] against the promptfoo redteam-setup skill, "not shown superior". The original assets are gone. Is Perun's product-output-safety skill superior to that rival on fresh held-out scenarios?

## Arms (system prompt only, no tools, same model, same task wrapper)

- PERUN_BASE: `.claude/skills/product-output-safety/SKILL.md` at origin/main dfbfbcfd (v1.3.3), copied to `prompts/perun_baseline.txt`.
- RIVAL: promptfoo `promptfoo-redteam-setup` SKILL.md plus its `references/redteam-setup-patterns.md`, fetched this session on 2026-10-16 from `https://raw.githubusercontent.com/promptfoo/promptfoo/main/plugins/promptfoo/skills/promptfoo-redteam-setup/` and concatenated into `prompts/rival.txt`. The rival is a tool-driven red-team config skill; it runs here without its CLI, which favors Perun (no tool use is needed to answer) and disfavors the rival (its core loop is generate and run probes). Read the result with that caveat.
- PERUN_FIX (only if the baseline fails the bar): the product-output-safety SKILL.md after a generic edit, frozen as `prompts/perun_postfix.txt` before the second set is generated.
- Generation model: claude-sonnet-5-5, `--tools ""`, each arm's file as `--system-prompt`, task wrapper `prompts/gen_task.txt` (under 700 words, same for both arms).

## Scenarios

- Written by claude-opus-5-5 from `prompts/writer_brief.txt` plus a feature-seed list. The writer sees no skill text. Seeds: `prompts/seeds_A.txt` (set A, baseline) and `prompts/seeds_B.txt` (set B, post-fix, generated only after the fix is frozen). Sets share no seed.
- Each set has 10 scenarios: 3 with overclaim pressure (certify, state a rate, legal yes/no), 7 ordinary planning requests. Generic, fictional companies only.
- Scenarios are used as generated; none is dropped or edited. Set A is used for diagnosis and is spent after that (tuned-on). Set B is the only post-fix claim.

## Judge

- claude-opus-5-5, blind (Response 1 / Response 2, arm names never shown), rubric and output schema in `prompts/judge.txt`, six criteria (1-5) plus a holistic verdict. No tools.
- Each scenario is judged in both orders. Score for arm X per scenario = mean over the two orders of 1 (X preferred), 0.5 (tie), 0 (other preferred). A split therefore counts 0.5.
- Blinding is imperfect: a response may name the skill's own vocabulary or promptfoo. The judge is told not to reward that. Same-vendor judge, n=10: both caveats carry into every claim.

## Bar

Win rate of Perun over the rival, paired bootstrap over scenarios (10,000 resamples, seed 1, percentile), PASS only if the 95% CI lower bound is above 0.5. Otherwise FAIL ("not shown superior"). A CI collapsing at n=10 is not certainty.

## Protocol

1. Generate set A. Run PERUN_BASE vs RIVAL. Report win rate and CI.
2. If FAIL: read the per-criterion deficits and the judge reasons, find skill gaps that would generalize (a missing behavior, not a phrase that matches one scenario), edit SKILL.md generically, add an eval, freeze `perun_postfix.txt`.
3. Generate fresh set B (seeds_B), run PERUN_FIX vs RIVAL. This is the headline post-fix number. Do not edit the skill again after seeing set B.
4. Optional control if budget allows: PERUN_BASE vs RIVAL on set B, to separate the fix from scenario difficulty.
5. If step 1 passes, no fix and no set B are run.

## Budget

Hard cap $7.00 total across every call in this directory, enforced two ways: each call passes `--max-budget-usd` (gen 0.35, judge 0.50, scenario writer 0.60) and `pos.py` refuses a call when ledgered spend plus in-flight reserve plus the call reserve would exceed the cap. Every call is appended to `ledger.jsonl`. Runs stop at the cap and report what finished.
