# Preregistration: superiority test of the shipped business-ops SKILL.md on 200 fresh held-out scenarios (2026-10-18)

Written before any seed, scenario or arm answer exists. Every model call goes to the PCSS endpoint ($0); no `claude -p`, no paid API, public data only. Scenarios file: scenarios-heldout.json. Hashes of every input are frozen in SHA256-frozen.txt, whose sha256 is the first ledger line (`preregistered`), written after the scenarios are frozen and before any arm answer is generated.

## Question

Does the business-ops `SKILL.md` as shipped at origin/main 06e6fa48 (sha256 39af659d0f34751f187cd40fe5e4ee9f7325d1b314485bbcf1633da87eecf741) beat its rival (marketingskills pricing, text sha256 b0318f64140e60a28d0cf71b1a6bf2aa214b96ef2bc3253c60d16ae480367d25, MIT, the same text as `../bizops-e-confirm-1018`) on scenarios neither the text nor its authors have seen? An earlier run (`../bizops-shipped-1018`, 0.580 [0.507, 0.650] on the c150 scenarios) is not fresh for this text, since c150 was used to choose and measure the lineage that produced it, and it carried no preregistered superiority rule.

## Decision rule (fixed now)

Claim superiority if and only if the win-rate 95% confidence interval lower bound is above 0.5 against the rival, over n=200 fresh held-out scenarios. Any other outcome, including a point estimate above 0.5 with a lower bound at or below 0.5, is reported as not a win. There is no second run, no extra scenarios, no change of judge and no `SKILL.md` edit after the result is seen, whichever way it goes.

## Arms

- PERUN: `prompts/perun_business-ops_shipped.txt`, a byte copy of `.claude/skills/business-ops/SKILL.md` at origin/main 06e6fa48, used as the system prompt. This is the only Perun arm.
- RIVAL: `prompts/rival_business-ops.txt`, a byte copy of `../bizops-e-confirm-1018/prompts/rival_business-ops.txt`, used as the system prompt.
- Both arms answer every scenario with the harness wrapper `GEN_TASK` (`scripts/rival_eval.py`), generator Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, unseeded sampling. Each arm is generated once; no regeneration.

## Scenarios

- 200 scenarios, ids s200-001 to s200-200, drawn fresh: 200 one-line settings from the generator (calls of 50 with the same ask as `../bizops-e-confirm-1018` plus a rotating industry-family focus, repeated until 200 lines are new against every earlier business-ops seed line and this draw; the earlier lines are filtered out afterwards, not shown to the generator, because showing them made it repeat them), then written into full requests by the harness writer brief (`scripts/eval-fixtures/rival/business-ops/brief.txt`, never shown any skill text).
- Disjointness is enforced mechanically by `bench.py check` against every scenario in every set under `docs/bench` and `scripts/eval-fixtures` (any JSON list of objects with a `prompt`, `ticket` or `text` field, all skills, tune and held, excluding this directory): no shared id, no identical normalized text, and for every pair (including pairs inside this set) the 6-word-shingle overlap `|A and B| / min(|A|, |B|)` is at most 0.10. A scenario that fails is redrawn from the same seed (up to 12 rounds); a seed that cannot pass is not replaced by a hand-written one and stops the run.
- The scenarios are written, checked and hashed before the ledger's first line; no arm answer is generated before that line.

## Judging and scoring

- Judge: `scripts/rival_eval.py` judge v2 with GLM-5.1 only (no cascade), both orders per scenario, random three-letter labels, no rubric. A scenario scores 1 (Perun wins both orders), 0 (rival wins both), else 0.5; an order with no usable verdict counts 0.5 and is reported.
- Win rate = mean scenario score. CI: percentile bootstrap, 10,000 resamples, seed 1, over scenarios (`rival_eval.boot`).
- Health: the judge's slot-1 rate (share of non-tie picks in the first position). If it falls outside 0.4 to 0.6, no superiority is claimed from this run regardless of the interval (the harness drops such a judge), and the numbers are still reported.
- Reported: win rate with CI, wins / ties / losses, slot-1 rate, failed orders. The c150 result is quoted for context and never pooled.

## Caveats declared in advance

Open models on one cluster; system-prompt-only arms; synthetic scenarios from a single writer; generator and judge are both open models run on the same cluster. The rule asks for a lower bound above 0.5 only, a low bar that says nothing about effect size or real-user value. A pass would be one preregistered, single-judge, single-generator result. The ledger (`ledger.jsonl`) is append-only (events `preregistered`, `gen`, `judge`).
