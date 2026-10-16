product-output-safety held-out re-test against the promptfoo redteam-setup skill, 2026-10-16. Cited by docs/perun-vs-rivals.md H1b.

- PREREGISTERED.md, PREREGISTERED-ADDENDUM-1.md (rubric-free judge and decision rule), PREREGISTERED-ADDENDUM-2.md (diagnosis, set B plan): written before the calls they govern.
- prompts/: frozen system prompts (perun_baseline.txt = SKILL.md v1.3.3 at origin/main dfbfbcfd, perun_postfix.txt = after the edit, rival.txt = promptfoo SKILL.md plus references/redteam-setup-patterns.md fetched 2026-10-16), writer brief, seeds, task wrapper, rubric judge (judge.txt) and rubric-free judge (judge_neutral.txt).
- scenarios/A.json, B.json: the 10 generated scenarios per set, used unedited.
- outputs/<set>/<arm>/<id>.txt: generated answers. judge/ (rubric) and judge_neutral/: per-order verdict JSON, folder name is <Response 1 arm>__<Response 2 arm>.
- results-*.json and results_neutral-*.json: win rates, bootstrap CI, per-criterion means (rubric judge only), cumulative spend.
- ledger.jsonl: every call and its cost (total $6.22; the first scen/A row is a zero-cost proxy failure before the allowed host was set). pos.py: the driver (`pos.py scen|run|report`, env JV=neutral for the rubric-free judge, JOBS for concurrency).
- SHA256-frozen.txt was taken before the first call; pos.py was edited afterwards only to add the JV and JOBS switches. Everything else listed there is unchanged.
- Not reproducible bit for bit: model sampling is not seeded. The control run (PERUN_BASE vs RIVAL on set B) used JOBS=1 after an earlier attempt stopped at the cost guard; the partial first attempt reused the same cached outputs.
- The skill is unchanged. An experimental SKILL.md edit tried after set A is not shipped: `prompts/perun_postfix.txt` is the tested text and Addendum 2 describes the diagnosis; the later decision not to ship it (n=10 and overlapping intervals show no gain, +1.5 KB per load) post-dates that addendum.

Third-party text: prompts/rival.txt is the promptfoo skill (plugins/promptfoo/skills/promptfoo-redteam-setup/SKILL.md and its references/redteam-setup-patterns.md, from the promptfoo repository, fetched 2026-10-16), included unmodified for reproducibility. Its license, fetched 2026-10-16 from the LICENSE file of the same repository, is the MIT License:

Copyright (c) Promptfoo 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
