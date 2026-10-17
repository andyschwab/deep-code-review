# Delivery-plan bench, 2026-10-17

Question: does `agentic-delivery` produce better delivery plans (lanes, gates, review, landing) than Superpowers (subagent-driven-development + writing-plans) and gstack `ship`? Preregistered in `PREREGISTERED.md`, rubric-free, blind, both judge orders, PCSS models only (0 paid calls).

Result: the baseline skill beats gstack ship on held-out tickets (0.667, 95% CI [0.521, 0.792]) and ties Superpowers (0.490, [0.354, 0.625]). One tune-only edit was tried and rejected (held-out vs Superpowers 0.542, [0.396, 0.688]; keep rule needs a lower bound above 0.5 against both rivals), so `SKILL.md` is unchanged. The full table, judge position-bias numbers and caveats are in the Outcome section of `PREREGISTERED.md`.

Files:
- `tickets.json`: 40 fictional tickets, 16 tune and 24 held-out (frozen split).
- `prompts/`: arm system prompts (`perun.txt` baseline, `perun2.txt` rejected candidate, `sp.txt`, `gs.txt`), ticket-writer brief, generation task, judge prompt.
- `outputs/<arm>/<ticket>.txt`: generated plans. `judge/<judge>/<A>__<B>/<order>/<ticket>.json`: verdict and one-line reason per order (`-t` dirs are the thinking judges).
- `results/*.json`: win rate, bootstrap CI, W/L/mixed and slot-1 rate per pair (`-t` suffix = thinking judge, the deciding instrument).
- `bench.py` driver, `run_iter.sh` and `finalize.sh` wrappers, `reasons.py` judge-reason reader, `ledger.jsonl` call log (model and token usage, no key).
- `SHA256-frozen.txt` (hashes at freeze) and `SHA256-amended.txt` (current `PREREGISTERED.md` and `bench.py`, after amendments A1 and A2).
- `rival/`: licences of the two rival skills; their commit shas are in `PREREGISTERED.md`.

Reproduce: `KEYFILE=<file with PCSS_KEY=...> JTHINK=1 NOGLM=1 python3 -I bench.py judge perun sp` then `python3 -I bench.py score perun sp`. Generation is unseeded, so regenerated plans will differ.
