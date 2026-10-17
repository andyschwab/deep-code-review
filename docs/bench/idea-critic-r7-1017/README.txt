idea-critic, round 7: c6 against v0 on 100 fresh held-out scenarios, 2026-10-17. Preregistration: PREREGISTERED.md (+ PREREGISTERED-ADDENDUM-1.md); hashes in SHA256-frozen.txt (taken before any round-7 generation) and SHA256-addendum1.txt (seeds and scenario file, before any answer); the timestamped preregistration line is the first line of ledger.jsonl. Rival answers frozen in RIVAL-sha256-r7.json. Driver bench7.py (derived from ../idea-critic-r6-1017/bench6.py; reuses ../exec-1017/bench.py); judge prompt v2 byte-identical to rounds 5 and 6; rival prompt reused from ../exec-1017/prompts. PCSS only, no paid call, no key printed.

Result: c6 is not shipped; .claude/skills/idea-critic/SKILL.md is unchanged. The rule was: ship only if the paired c6 minus v0 95% bootstrap lower bound is above 0. It is -0.045.

Held-out, 100 scenarios r7-001..r7-100 (ids, company names, exact texts and 30-word shingles disjoint from every earlier file; bench7.py check), same frozen rival answers, judges GLM-5.1 + GLM-5.2 + gpt-oss_120b, both orders, strict agreement else tie, majority of three, ties count 0.5, bootstrap 10,000 resamples seed 1:
  v0 (SKILL.md at this commit): win rate against rival 0.490, 95% interval [0.410, 0.570], 30 wins / 38 ties / 32 losses, order disagreement 0.310.
  c6 (round-6 candidate):       win rate against rival 0.535, 95% interval [0.455, 0.615], 35 wins / 37 ties / 28 losses, order disagreement 0.330.
  paired c6 minus v0: +0.045, 95% interval [-0.045, 0.140] (results7-paired.json). Not significant, so the edit is not kept.
  Neither arm's lower bound is above 0.5, so neither is shown to beat the rival; c6's win rate (0.535) is above 0.5 but within noise.
Across rounds, v0 against the rival: 0.575 (r5, n=40), 0.475 (r6, n=40), 0.490 (r7, n=100); c6: 0.550 (r6, n=40), 0.535 (r7, n=100). The pooled picture is a tie with the rival, with a point estimate favouring c6 by roughly 0.05 that this design cannot confirm.

Caveats: open models on one cluster; system-prompt-only arms; ties are 37-38 of 100; one run per arm; gpt-oss_120b writes seeds and scenarios and also judges; the scenario sets are model-written; the c6 text came from the round-6 tune, so this set is a clean held-out for it. The 10-word shingle disjointness check of PREREGISTERED.md flagged shared ask-template sentences in 97 of 100 scenarios and was raised to 30 words (addendum 1, before any answer). A first background launch of the rival generation failed on network errors (400 URLError lines in ledger.jsonl) and wrote no answers; it was rerun in the foreground with nothing else changed. 32 HTTPError and 3 IncompleteRead lines are retried calls; every one of the 1,200 judge orders parsed.

Review notes (independent review of PR #1645; all headline numbers recomputed exactly from the judge files, 300 cells per arm):
- Text disjointness. Addendum 1 moved the overlap check from 10-word to 30-word shingles, which cannot catch copied passages
  shorter than 30 words. Re-checked at 10 words, 97 of 100 scenarios share at least one 10-word run with an earlier round.
  The shared runs are template phrases that the scenario writer reuses (for example the fictional persona introduction line),
  each found in at most 2 earlier scenarios. No scenario is a copy of an earlier one. A future round should allowlist the
  template phrases before generation and keep the 10-word check.
- PREREGISTERED.md section 2 names SHA256-scenarios7.txt, which does not exist. The scenario hashes are in SHA256-addendum1.txt,
  recorded at ledger entry 105, before the first answer at entry 106.
- SHA256-frozen.txt hashes bench7.py before the addendum edit. The pre-edit file is not committed, so the edit itself can be
  checked only through the addendum text.
