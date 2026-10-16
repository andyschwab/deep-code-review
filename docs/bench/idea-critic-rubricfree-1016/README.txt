idea-critic vs its H1 rival, rubric-free blind judge re-test, 2026-10-16. Cited by docs/perun-vs-rivals.md H1 and H1d.

Result: Perun win rate 0.650, 95% CI [0.450, 0.850], n=10, 5 of 10 scenarios split by order. FAIL against the preregistered bar (CI lower bound above 0.5). Spend $1.50 (ledger.jsonl, 41 calls, 0 errors). Rival: garrytan/gstack plan-ceo-review/SKILL.md (commit 47d639ab, MIT).

Perun clear wins in 4 scenarios (01, 04, 05, 06), a clear loss in 1 (09), 5 split by order (02, 03, 07, 08, 10). The 20 judge reasons that favour the rival cite more actionable, more complete briefs (phased paths, sharper questions); those that favour Perun cite arithmetic accuracy and sharper insights. A tie at n=10 that the data cannot separate from a loss or a modest win; the earlier 1.000 came from a rubric that was not preserved and is not reproduced.

- PREREGISTERED.md: pair choice, arms, judge, bar, stop rule. Written and hashed before the first call of any of the five re-tests (SHA256-frozen.txt).
- prompts/: perun.txt (the skill's SKILL.md at origin/main 6bb9a707), rival.txt (unmodified rival text, see PREREGISTERED.md for files and license), gen_task.txt, writer_brief.txt, seeds.txt, judge.txt (no criteria). LICENSE.rival.txt is the rival repository's MIT license, fetched 2026-10-16 at the same commit.
- scenarios.json: 10 generated scenarios, used unedited. outputs/<ARM>/<id>.txt: generated answers. judge/<Response 1 arm>__<Response 2 arm>/<id>.json: per-order verdict and one-sentence reason.
- results.json: per-scenario scores, win rate, bootstrap CI (10,000 resamples, seed 1, percentile). bench.py: driver copied from docs/bench/comms-rubricfree-1016/bench.py with two edits (cap read from the CAP env var so the runs share one $6 total; temp-dir prefix).
- Not reproducible bit for bit: model sampling is not seeded. Same-vendor judge, one set of 10; both caveats apply. Both arms ran without tools, so the skill's references and scripts were unavailable to Perun.
- The skill is unchanged.
- Trailing spaces (markdown line breaks) were stripped from outputs/RIVAL/06.txt in the committed copy only, so the diff whitespace check passes; the judge saw the original text.
