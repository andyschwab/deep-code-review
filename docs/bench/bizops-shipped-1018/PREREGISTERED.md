# Preregistration: shipped business-ops SKILL.md on the c150 scenarios (2026-10-18)

Written and hashed (SHA256-frozen.txt, ledger.jsonl first line `preregistered`) before any generation or judge call of the shipped arm. Every model call goes to the PCSS endpoint ($0); no `claude -p`, no paid API, public data only. Code derived from `../bizops-e-confirm-1018/bench.py`.

## Question

`../bizops-e-confirm-1018` measured the frozen "lead with the call" text e (sha256 d0f49e79...) at 0.563 [0.490, 0.633] on its 150 scenarios, and `docs/perun-vs-rivals.md` cites that number for business-ops. The text actually shipped in `.claude/skills/business-ops/SKILL.md` (sha256 39af659d..., at origin/main 06e6fa48) is not byte-identical to e: it differs by 16 lines (a reworded frontmatter description and two changed Verification bullets) and was never benched as shipped. This run measures the shipped text itself on the same scenarios.

This is a descriptive check, not a keep or ship decision: no `SKILL.md` edit follows from any result, and there is no decision rule beyond reporting the numbers below.

## Arm and inputs (all read in place from `../bizops-e-confirm-1018`, nothing copied or regenerated)

- shipped: `prompts/perun_business-ops_shipped.txt`, a byte copy of `.claude/skills/business-ops/SKILL.md` at origin/main 06e6fa48, sha256 39af659d0f34751f187cd40fe5e4ee9f7325d1b314485bbcf1633da87eecf741.
- Scenarios: `../bizops-e-confirm-1018/scenarios/business-ops-c150.json`, ids c150-001 to c150-150, unedited.
- Rival answers: the 150 committed files `../bizops-e-confirm-1018/outputs/RIVAL/*.txt` (generated once by the earlier round, reused as is, so the rival side is identical to the e and v0 comparisons). Rival text `prompts/rival_business-ops.txt` of that round, sha256 b0318f64..., MIT.
- Earlier arms: `results/c150-e.json` and `results/c150-v0.json` of that round (per-scenario scores), used only for the paired differences.
- Every input above is hashed in SHA256-frozen.txt.

## Generation, judging, scoring (same as the earlier round)

- Generator: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, harness `GEN_TASK` wrapper, system prompt = the arm text. Sampling is unseeded.
- Judge: `scripts/rival_eval.py` judge v2 with GLM-5.1 only, the judge that scored e and v0 (slot-1 rate 0.511 there). No cascade, so the paired differences use one judge. The shipped arm's own slot-1 rate is reported, and if it falls outside 0.4 to 0.6 that is stated as a caveat and the numbers are still reported, not swapped for another judge.
- Both orders per scenario; a scenario scores 1 (Perun wins both), 0 (rival wins both), else 0.5; an order with no usable verdict counts 0.5 and is reported.
- Win rate = mean scenario score. CI: percentile bootstrap, 10,000 resamples, seed 1, over scenarios.
- Reported: shipped win rate against the rival with CI and wins / ties / losses; paired shipped minus e (primary) and shipped minus v0 (context) over the same 150 scenarios, same bootstrap.

## Caveats declared in advance

Open models on one cluster; system-prompt only arms; same-vendor judge and generator family. The shipped and e generations are separate unseeded samples, so a paired difference includes sampling noise as well as the 16-line text difference; a near-zero paired difference does not show the 16 lines are neutral. The paired CI is the only uncertainty reported for it. Nothing here is edited or re-run after a result is seen; the ledger (`ledger.jsonl`) is append-only (events `preregistered`, `gen`, `judge`, `paired`).
