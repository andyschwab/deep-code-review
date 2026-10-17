# Tune result and choice (recorded 2026-10-17, after the tune run and before any held-out generation)

Tune n=10 (old scenarios 01-10), judge prompt v2, GLM-5.1 + GLM-5.2 + gpt-oss_120b, both orders, strict agreement, majority (`results5-*-tune-v2.json`, `judge5/v2/tune/`):

| arm | win rate vs rival | 95% interval | wins / ties / losses |
|---|---|---|---|
| v0 (current SKILL.md) | 0.75 | [0.55, 0.95] | 6 / 3 / 1 |
| c5 (leading tripwire clause, step 6) | 0.65 | [0.40, 0.90] | 5 / 3 / 2 |

Decision by the preregistered rule (section 4): c5 is below v0 on tune, so the edit is not taken forward and `SKILL.md` stays unchanged (reverted; nothing was ever written to it, the candidate lives only in `prompts/perun_idea-critic_c5.txt`). Tune at n=10 is a weak selector and this is a one-scenario gap, but the rule was fixed in advance and is followed.

Held-out: the edit does not go to held-out. The fixture fix (judge v2) does change what v0 scores against the rival, which round 4 could not show, so v0 alone is run once on the fresh 40 scenarios as a reference measurement (same protocol, same frozen RIVAL files). It carries no keep or revert decision; there is no edit to keep.
