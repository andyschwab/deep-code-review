product-output-safety held-out re-test against the promptfoo redteam-setup skill, 2026-10-16. Cited by docs/perun-vs-rivals.md H1b.

- PREREGISTERED.md, PREREGISTERED-ADDENDUM-1.md (rubric-free judge and decision rule), PREREGISTERED-ADDENDUM-2.md (diagnosis, set B plan): written before the calls they govern.
- prompts/: frozen system prompts (perun_baseline.txt = SKILL.md v1.3.3 at origin/main dfbfbcfd, perun_postfix.txt = after the edit, rival.txt = promptfoo SKILL.md plus references/redteam-setup-patterns.md fetched 2026-10-16), writer brief, seeds, task wrapper, rubric judge (judge.txt) and rubric-free judge (judge_neutral.txt).
- scenarios/A.json, B.json: the 10 generated scenarios per set, used unedited.
- outputs/<set>/<arm>/<id>.txt: generated answers. judge/ (rubric) and judge_neutral/: per-order verdict JSON, folder name is <Response 1 arm>__<Response 2 arm>.
- results-*.json and results_neutral-*.json: win rates, bootstrap CI, per-criterion means (rubric judge only), cumulative spend.
- ledger.jsonl: every call and its cost (total $6.22; the first scen/A row is a zero-cost proxy failure before the allowed host was set). pos.py: the driver (`pos.py scen|run|report`, env JV=neutral for the rubric-free judge, JOBS for concurrency).
- SHA256-frozen.txt was taken before the first call; pos.py was edited afterwards only to add the JV and JOBS switches. Everything else listed there is unchanged.
- Not reproducible bit for bit: model sampling is not seeded. The control run (PERUN_BASE vs RIVAL on set B) used JOBS=1 after an earlier attempt stopped at the cost guard; the partial first attempt reused the same cached outputs.
