Positioning and business-ops against their strongest public rival, round 3, 2026-10-17. Preregistration: PREREGISTERED.md and PREREGISTERED-ADDENDUM-1.md (hashes frozen before any generation in SHA256-frozen.txt, SHA256-amend.txt, SHA256-selection.txt). All calls on the PCSS endpoint, $0.

Held-out, n=40 fresh fictional scenarios per skill, Perun win rate against the rival (1 Perun, 0.5 tie, 0 rival), bootstrap 95% interval, three judges (DeepSeek-V4-Flash, GLM-5.2, MiniMax-M2.5), both orders each, strict agreement, majority decides:
  skill         v0 (unedited)               selected edit                  decision
  positioning   0.675 [0.562, 0.775]        a  0.787 [0.688, 0.887]        kept (lower bound above 0.5, and at least v0)
  business-ops  0.287 [0.163, 0.412]        c  0.338 [0.225, 0.463]        reverted (lower bound not above 0.5)
Strict counts (win/tie/loss): positioning v0 19/16/5, a 27/9/4; business-ops v0 8/7/25, c 8/11/21.
Paired difference, positioning a minus v0, same 40 scenarios and same rival answers: +0.1125, bootstrap 95% [0.013, 0.213].
Per judge, positioning a: DeepSeek 0.762, GLM 0.762, MiniMax 0.812 (v0: 0.725, 0.713, 0.575). Per judge, business-ops c: 0.325, 0.338, 0.400 (v0: 0.300, 0.312, 0.300). Slot-1 rates over all calls are in results/*.json (DeepSeek 0.475-0.525, GLM 0.56-0.64, MiniMax 0.60-0.68; GLM and MiniMax lean to slot 1, which is why only both-order agreement counts).

Tune (n=10, selection only), v0 / a / b / c: positioning 0.50 / 0.80 / 0.55 / 0.60; business-ops 0.55 / 0.45 / 0.50 / 0.60. Selection rule picked positioning a and business-ops c.

What shipped: the positioning edit (one new section, "Deliver the call, not a menu", 623 bytes in SKILL.md) and one eval. The business-ops edit is preserved only as edits-reverted-business-ops.patch; business-ops SKILL.md is unchanged.

Findings, stated plainly:
- The earlier "both near 0.5" readings were small-n. At n=40 unedited positioning already beats its rival (lower bound 0.562) and the edit adds a modest gain; unedited business-ops loses clearly to marketingskills pricing (0.287).
- The business-ops candidates (commit on the user's options, closing-line disclaimer, route with substance) did not move it: 0.338 against 0.287, intervals overlap. Its losses are not explained by the hedging root cause alone; the rival is a full pricing playbook and the Perun arm has no references or tools here, so a SKILL.md-only edit may not close this gap.
- Not tested: the "check the user's numbers first" candidate (positioning b, tune 0.55) was not selected; the briefs here do not plant numeric flaws.

Caveats: generator, writer and judges are open models on one cluster (not the models users run); both arms are system-prompt only, without references, scripts or tools; sampling is unseeded, so a re-run differs (earlier rounds moved about 0.1 on re-judging); best-of-three on n=10 tune overfits, so the held-out set, not tune, decides. The positioning rival is CC BY-NC-SA 4.0 text, so its text and outputs derived from it are not committed (hash in PREREGISTERED.md; the positioning judge records are committed, so the rival side cannot be re-judged from this tree). The business-ops rival text is not duplicated either (hash recorded; it matches docs/bench/exec-1017/prompts/rival_business-ops.txt).

Reproduce: python3 -I bench.py run SKILL ARM SPLIT (SKILL positioning or business-ops; ARM v0, a, b or c; SPLIT tune or heldout); needs PCSS_KEY in the environment or the repo-root .env, and the rival text fetched from the URL in scripts/eval-fixtures/rival/<skill>/rival.json.
