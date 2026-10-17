# Tune result and choice (recorded 2026-10-17, after the tune run and before any held-out generation)

Tune n=10 (old scenarios 01-10), judge prompt v2, GLM-5.1 + GLM-5.2 + gpt-oss_120b, both orders, strict agreement, majority (`results6-*-tune-v2.json`, `judge6/v2/tune/`):

| arm | win rate vs rival | 95% interval | wins / ties / losses |
|---|---|---|---|
| v0 (current SKILL.md; copied from round 5) | 0.75 | [0.55, 0.95] | 6 / 3 / 1 |
| c6 (bounded first step, numeric dated tripwire, figure error first; step 6) | 0.80 | [0.60, 1.00] | 7 / 2 / 1 |

By the preregistered rule (section 4) c6 is strictly above v0, so it goes to held-out. The gap is one scenario; tune n=10 is a weak selector. Held-out is run once with the unchanged protocol: fresh 40 scenarios, v0 and c6 on the same frozen RIVAL answers.
