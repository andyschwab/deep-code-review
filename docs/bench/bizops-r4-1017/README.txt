Business-ops against its strongest public rival (marketingskills pricing), round 4, 2026-10-17. Preregistration: PREREGISTERED.md, PREREGISTERED-ADDENDUM-1.md, PREREGISTERED-ADDENDUM-2.md (hashes in SHA256-frozen.txt, SHA256-frozen-addendum-1.txt, SHA256-scenarios.txt, SHA256-selection.txt). All calls on the PCSS endpoint, $0.

Result: reverted. The business-ops SKILL.md is unchanged; nothing ships except this bench.

Held-out, n=40 fresh fictional scenarios (disjoint from every earlier set, `bench.py check` clean), Perun win rate against the rival (1 Perun, 0.5 tie, 0 rival), bootstrap 95% interval, three judges (DeepSeek-V4-Flash, GLM-5.2, MiniMax-M2.5), both orders each, strict agreement, majority decides, generator never a judge, rival generated once and shared:
  v0 (unedited)          0.312 [0.200, 0.425]   5 wins / 15 ties / 20 losses
  b (selected on tune)   0.350 [0.225, 0.475]   8 / 12 / 20   paired gain over v0 +0.037 [-0.025, 0.100]
Keep rule (lower bound above 0.5 and at least v0): failed. Unedited business-ops reproduces round 3 (0.287 then, 0.312 now).

Tune (n=10, selection only): v0 0.50, a 0.55, b 0.65, c 0.50, d 0.60 (d, a plus b, was added in Addendum 1 after the first three tune runs and before any held-out use; b won the preregistered rule).

Exploratory, after the verdict (Addendum 2; not eligible for a keep decision; same held-out set and rival answers): a 0.300 [0.212, 0.400], c 0.450 [0.325, 0.562], d 0.400 [0.300, 0.500]. c, the restructure (one memo shape, three confidence tiers, 1 KB smaller than v0), is the best of five and the only one whose interval reaches above 0.5 at its upper end; it was picked on this set, so its 0.450 is optimistic and would need a fresh held-out set and a new preregistration.

Root cause (details and the behavior table in PREREGISTERED.md): the gap is skill content, not length or scope alone. Rival answers that win are as long as Perun's (529 vs 554 words) and carry as many numbers (35 vs 37). They win on posture: the call first, a substantive answer to legal, tax, accounting and regulatory questions with a one-line closing consult note, labelled assumptions computed through, and a trigger tied to the user's figures. Perun v0 opens with a disclaimer and a "Lane R: Route Immediately" banner, defers (defer/route wording in 17 of 28 lost scenarios), leaves formulas with blank variables, and prints its internal lane taxonomy. Hedge words per answer: 1.1 for the rival in its wins, 5.5 for Perun in the same scenarios. Scope mismatch is real but secondary: half the harness scenarios ask a regulation-dependent question where Perun's own rule is "route, never conclude" and the rival, a pricing playbook with no such rule, simply answers; the judge rubric rewards that. Single edits to one rule (a: format, b: Lane R content) move the rate by under 0.05; only the restructure that changes shape and content together moved it (c, exploratory +0.14 over v0).

What would be needed to ship a win: a SKILL.md that changes the output shape (answer first, no lane labels, closing disclaimer, assumptions computed) and the Lane R posture (general rule and usual practice answered, only the binding determination routed) together, tested on a fresh held-out set. That is a deliberate loosening of "route, never conclude" and an owner call, because the bench rewards substantive answers and does not measure the harm of a confident wrong legal or tax answer.

Caveats: generator, writer and judges are open models on one cluster (not the models users run); both arms are system-prompt only, without references; sampling is unseeded so a re-run differs (earlier rounds moved about 0.1); best-of-several on n=10 tune overfits; GLM and MiniMax lean to slot 1 (slot-1 rates in results/*.json), which is why only both-order agreement counts; the rival is a pricing skill answering questions outside its remit, so this measures answer-first helpfulness, not safety.

Reproduce: python3 -I bench.py run business-ops ARM SPLIT (ARM v0, a, b, c or d; SPLIT tune or heldout); needs PCSS_KEY in the environment or the repo-root .env and prompts/rival_business-ops.txt (sha256 in SHA256-frozen.txt; the same file is committed under docs/bench/exec-1017/prompts). python3 -I mkvariants.py rebuilds the arm prompts from SKILL.md.

Review notes (added after independent review):
- This bench has no call ledger with timestamps, so the claim that the preregistration and addenda were frozen before held-out generation rests on the committed hashes and the prose, not on call order.
- SHA256-frozen-addendum-1.txt hashes PREREGISTERED-ADDENDUM-1.md before its Selection section was appended; the hash of the final file is in SHA256-selection.txt.
- "17 of 28 losses defer" comes from a keyword scan of the posbiz-r3 judge records; depending on the pattern used it ranges from 16 to 18. No script for it is committed.
- Rival license: MIT, notice at ../growth-analytics-rubricfree-1016/LICENSE.rival.txt (same upstream repository and commit as the rival prompt used here).
