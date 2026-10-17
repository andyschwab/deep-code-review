# Preregistration: business-ops "lead with the call", against its strongest rival, round 5 (2026-10-17)

Written and hashed (SHA256-frozen.txt) before any seed, scenario, tune or held-out generation and before any judge call. Every model call goes to the PCSS endpoint ($0); no `claude -p`, no paid API, public data only. Code derived from `docs/bench/bizops-r4-1017`.

## Owner decision under test

Business-ops leads with the call. It answers legal, tax and accounting questions on the general rule with labelled assumptions and computed figures (no blank variables, no disclaimer banner, no lane labels), and keeps a short routing note only for jurisdiction-specific or high-stakes items. Round 4 (`../bizops-r4-1017`) found the restructure candidate c at 0.450 on a set it was picked on (exploratory, optimistic); this round tests it, and a rewording to the owner decision, on a fresh held-out set.

## Arms

- v0: the unedited `.claude/skills/business-ops/SKILL.md` at base commit 3d9a30ff (origin/main, sha256 daa7139a..., identical to round 4's v0).
- Candidates (exact text built by `mkvariants.py` into `prompts/perun_business-ops_{c,d,e}.txt`; the shipped SKILL.md is the selected candidate byte for byte): c = round 4's restructure (one memo shape, three confidence tiers); d = round 4's a+b (small edits: disclaimer last, "Lead with the call", Lane R explains the rule and routes the binding call); e = c reworded to the owner decision (general rule plus computed figures for legal, tax, accounting; one-sentence closing disclaimer; routing note of one or two lines only for jurisdiction-specific or high-stakes items). All three also update the frontmatter description so it no longer promises "routes to a professional" as the lead.
- Rival: marketingskills pricing SKILL.md (`prompts/rival_business-ops.txt`, sha256 b0318f64140e60a28d0cf71b1a6bf2aa214b96ef2bc3253c60d16ae480367d25, MIT, notice in `LICENSE.rival.txt`). The rival answer is generated once per scenario and shared by every Perun arm.

## Scenarios

Fresh and disjoint: 70 one-line settings drawn once by Qwen3.5-397B-A17B with the harness and round-3/4 settings listed as "do not repeat"; about half ask for a legal, tax, accounting or regulatory question (the requesting posture the owner decision is about). Seeds 01-10 give tune (n=10, ids t01-t10); seeds 11-70 give held-out (n=60, ids h01-h60). Written by the same blind writer (temperature 0.7, 10 per call) from the standing harness brief `scripts/eval-fixtures/rival/business-ops/brief.txt`, unedited, none dropped. `bench.py check` must report clean (no identical prompt, no 6-word-shingle overlap above 0.3 with the harness sets, `exec-1017`, round 3, round 4, or between this round's splits) before any arm runs; a failing writer output is redrawn once as a whole, never edited.

## Generation, judging, scoring

- Generator for every arm: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, harness `GEN_TASK` wrapper, system prompt = the arm text. Writer and generator never judge.
- Judge: `scripts/rival_eval.py` judge v2 (neutral three-letter labels, reason-first), cascade GLM-5.1, then GLM-5.2, then gpt-oss_120b; the first judge whose slot-1 rate over every verdict of the split lies in 0.4-0.6 scores all arms of that split; none healthy means no verdict. Both orders for every pair; a scenario scores 1 (Perun wins both), 0 (rival wins both), else 0.5; a judge order that returns no usable verdict counts as 0.5 and is reported. Existing records are never overwritten; runs are sequential.
- Win rate = mean scenario score. CI: percentile bootstrap, 10,000 resamples, seed 1, over scenarios. Paired difference = mean of (edit score - v0 score) per scenario, same bootstrap.

## Procedure and keep rule

1. Tune (n=10): v0, c, d, e vs the rival. Selection only; no verdict.
2. Selection: highest tune win rate among c, d, e; ties go to the smaller SKILL.md, then the earlier letter. Frozen in `SHA256-selection.txt` (hash of the tune results) before any held-out arm generation. The selected candidate runs on held-out even if it does not beat v0 on tune.
3. Held-out (n=60): v0 and the selected candidate once each, same rival answers, same judge. No re-runs, no judge swaps, no scenario edits after a result is seen.
4. SHIP the SKILL.md edit only if the paired (edit - v0) 95% bootstrap CI lower bound is above 0 on held-out. Otherwise revert the SKILL.md edit and ship only the bench and its record. Superiority over the rival is claimed only if the edit's own win-rate CI lower bound is above 0.5.

## Caveats declared in advance

Open models on one cluster, not the models users run; both arms system-prompt only (the Perun arm sees SKILL.md without references or scripts). Sampling is unseeded; earlier re-judges moved about 0.1. The rival is a pricing skill answering legal, tax and regulatory questions it was not written for, and the judge rubric rewards substantive, decisive answers, so a win measures answer-first helpfulness, not safety. Candidates loosen "route, never conclude" by design (the owner decision); the no-fabrication floor (UNVERIFIED on unverifiable specifics, the securities boundary, the never-fabricate lines) is kept, and the matching eval and changelog state the loosening plainly.
