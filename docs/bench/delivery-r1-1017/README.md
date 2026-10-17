# Delivery-plan bench, round 1, 2026-10-17

Question: does a small edit to `agentic-delivery/SKILL.md` make delivery plans better than Superpowers (subagent-driven-development plus writing-plans)? Preregistered in `PREREGISTERED.md` (frozen hashes in `SHA256-frozen.txt`), three blind judges both orders, strict agreement then majority, PCSS models only (0 paid calls).

Result: held-out (n=40 fresh tickets) the baseline scores 0.613 [0.537, 0.688] against Superpowers, the candidate paragraph (`edits/e1.txt`) 0.637 [0.550, 0.725], and the SKILL.md that ships (that paragraph plus about 370 bytes of tightened wording so the file stays under the 24000-byte cap, `prompts/ship.txt`) 0.688 [0.588, 0.775]. The shipped text is not separable from the baseline (paired difference +0.075, CI [-0.050, 0.188]); see the Outcome section for the caveats.

Files: `bench.py` (generate, judge write-once, score), `run_tune.sh`, `run_held.sh`, `prompts/` (baseline and shipped skill text, held-out seeds), `edits/` (three candidate paragraphs; only `e1.txt` ships), `tickets.json` (40 held-out tickets), `outputs/<arm>/<ticket>.txt`, `judge/<judge>/<arm>__sp/<order>/<ticket>.json`, `results/`, `void-tune-pass1/` (a voided pass, see Amendment A1). Re-run: `PCSS_KEY=... ./run_tune.sh` then `./run_held.sh v0 e1`, then `./run_held.sh ship`.
