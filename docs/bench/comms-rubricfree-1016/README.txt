communication-structure vs humanizer, rubric-free blind judge re-test, 2026-10-16. Cited by docs/perun-vs-rivals.md H1 and H1c.

Result: Perun win rate 0.500, 95% CI [0.250, 0.800], n=10, 2 of 10 scenarios split by order. FAIL against the preregistered bar (CI lower bound above 0.5). A tie that the data cannot separate from a loss or a win. Spend $0.93 of the $6 cap (ledger.jsonl, 41 calls, 0 errors).

- PREREGISTERED.md: pair choice, arms, judge, bar. Written and hashed before the first call (SHA256-frozen.txt).
- prompts/: perun.txt (communication-structure SKILL.md v1.2.4 at origin/main 350274b2), rival.txt (humanizer SKILL.md v3.1.0, blader/humanizer commit 225a6f39, fetched 2026-10-16, unmodified), gen_task.txt, writer_brief.txt, seeds.txt, judge.txt (no criteria, "which would you rather receive").
- scenarios.json: 10 generated scenarios, used unedited (1-5 write from facts, 6-10 rewrite a draft). outputs/<ARM>/<id>.txt: generated answers. judge/<Response 1 arm>__<Response 2 arm>/<id>.json: per-order verdict and one-sentence reason.
- results.json: per-scenario scores, win rate, bootstrap CI (10,000 resamples, seed 1, percentile). bench.py: driver, adapted from docs/bench/pos-1016/pos.py (`bench.py scen|run|report`).
- Not reproducible bit for bit: model sampling is not seeded. Same-vendor judge, one set of 10; both caveats apply. Both arms ran without tools, so the skill's lint scripts and references were unavailable to Perun.
- The skill is unchanged.

Third-party text: prompts/rival.txt is the humanizer skill (SKILL.md from the blader/humanizer repository, fetched 2026-10-16), included unmodified for reproducibility. Its license, fetched 2026-10-16 from the LICENSE file of the same repository at the same commit, is the MIT License; the full text is in LICENSE.rival.txt (copyright line: "Copyright (c) 2025 Siqi Chen").
