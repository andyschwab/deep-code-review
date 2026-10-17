# Preregistration: business-ops against its strongest rival, round 4 (2026-10-17)

Written and hashed (SHA256-frozen.txt) before any seed, scenario, tune or held-out generation and before any judge call. Every model call goes to the PCSS endpoint ($0); no `claude -p`, no paid API. Procedure and code are derived from `docs/bench/posbiz-r3-1017` (round 3).

## Baseline

Round 3 held-out, n=40, three judges, both orders, strict agreement: unedited business-ops 0.287 [0.163, 0.412] against marketingskills pricing; best edit 0.338 [0.225, 0.463]; reverted. Earlier: `exec-1017` round 2 (n=20) 0.475 [0.300, 0.625]; `rival-eval-baseline-1017` (n=10) 0.400 [0.150, 0.700].

## Root cause (read from every round-3 judge reason where the rival won, 28 v0 and 23 c losses over the 50 tune and held-out scenarios, and 326 rival-favoring reasons across rounds 1 to 3; outputs compared side by side, e.g. h25, h37)

Gap is skill content, not length. When the rival wins, its answer is as long as Perun's (529 vs 554 words on average; numbers per answer 35 vs 37), so length is not the lever. The lever is posture. Perun's text sets a refusal-first output shape that the generator follows closely:

| Behavior | Rival (wins) | Perun v0 (loses) |
|---|---|---|
| Opening | The call in the first sentence ("adopt 5.5-year straight line, zero salvage"; "reject as structured"; "take the PPA with a partnership") | Standing disclaimer first, then a "Lane R: Route Immediately" banner and "unauthorized practice of accounting" |
| Legal, tax, accounting, regulatory question | Answers on the general rule and usual practice (depreciation choice, 510(k) vs De Novo costs and timelines, FAR progress-payment structure, journal entries), one closing "consult a CPA" line | Names the regime and routes; "primarily defers to external professionals" (defer/route/deflect wording in the winning-rival reasons of 17 of 28 v0 losses) |
| Missing inputs | States an assumption, computes it (IRR 18-22%, $8,100 subsidy cost, 3-shift stadium model) | Leaves "formulas with undefined variables" and "placeholders"; "never fabricate inputs" is read as "do not compute" (placeholder/undefined-input wording in 5 of 28 v0 losses) |
| Options the user posed | Picks one and gives clauses, tiers, surcharge line, pilot size | Presents scenarios A/B/C and says the decision is the user's |
| Stop or pivot trigger | Tied to the user's figures with a threshold | Generic checklist ("compile the raw data and deliver to a CPA") |
| Structure | One recommendation, short justification, one note line | Internal taxonomy printed ("Lane A", "Lane R"), caveat lines before and after |
| Hedge density (consult/attorney/professional/hypothesis words per answer) | 1.1 in rival wins | 5.5 in the same scenarios |

Scope or format mismatch is secondary but real: the harness scenarios (standing briefs, not edited here) ask for a substantive answer and say what the requester wants back, and half ask a legal, tax, accounting or regulatory question where Perun's Lane R rule says "route, never conclude". The rival is a pricing playbook with no such rule, so it answers. Round 3's "route with substance" and "commit" edits were small additions inside that same posture (disclaimer moved, one bullet each) and moved the rate by 0.05, within noise. This round tests format, content and a restructure.

## Candidates (exact text in `mkvariants.py`, built into `prompts/perun_business-ops_{a,b,c}.txt`; the arm text is the shipped SKILL.md, byte for byte)

- a (format, small): disclaimer becomes the closing line, never the opener; new section "Lead with the call": verdict first, flip input and a computed stop trigger, no lane labels, choose between options the user posed, labelled low/base/high assumptions when the user's figures bracket a missing input (a bare "fill in our CAC" still returns the formula).
- b (content, medium): Lane R becomes "explain the rule, route the binding call": general rule, usual practice, flip facts, illustrative figure on the user's numbers when asked, UNVERIFIED on recalled specifics; only the binding determination (filing, amount owed, "you are covered", what an instrument permits) is routed with the exact question to bring. Anti-rationalization rows and Definition of done follow.
- c (larger restructure): the two-lane text is replaced by one memo shape (call, numbers with labelled assumptions, flip input and trigger, what to confirm and with whom) and three tiers by confidence (compute, explain and recommend, route). Keeps the securities boundary, the never-fabricate rules (first lines unchanged for the rules gate), design-time triage, stage awareness, definition of done, anti-rationalization table and verification list. Smaller than v0 (10.7 KB vs 11.5 KB).
- v0: the unedited `.claude/skills/business-ops/SKILL.md` at base commit 78ab50cf (origin/main, v1.589.0); identical bytes to round 3's v0 (sha256 daa7139a...).

## Scenarios

Fresh and disjoint. Fifty one-line settings drawn once by Qwen3.5-397B-A17B with the round-3 settings listed as "do not repeat" (`prior/seeds_business-ops-r3.txt`). Seeds 01-10 give tune (n=10, ids t01-t10); seeds 11-50 give held-out (n=40, ids h01-h40). Written by the same blind writer (temperature 0.7, 10 per call) from the standing harness brief `scripts/eval-fixtures/rival/business-ops/brief.txt` (no skill or rival text), used unedited, none dropped. `bench.py check` must report clean before any arm runs: no identical prompt, no 6-word-shingle overlap above 0.3 with the harness sets, the `exec-1017` sets, the round-3 sets (`prior/`), or between this round's splits. If the writer's output fails the check, it is redrawn once as a whole, never edited.

## Arms, judges, scoring

- Generator for every arm: Qwen3.5-397B-A17B, thinking off, temperature 0.3, no tools, harness `GEN_TASK` wrapper, system prompt = the arm text. Rival text: marketingskills pricing SKILL.md, sha256 b0318f64140e60a28d0cf71b1a6bf2aa214b96ef2bc3253c60d16ae480367d25 (same as rounds 1 to 3). The rival answer is generated once per scenario and shared by every Perun arm.
- Judges: DeepSeek-V4-Flash, GLM-5.2 (thinking off), MiniMax-M2.5; harness rubric-free blind prompt; every pair in both orders; a judge's vote counts for an arm only when both orders agree, else tie; majority of the three decides, else tie (0.5). Generator and writer never judge. A judge call that fails is retried up to three times; a still-failed order counts as a tie vote and is reported. Existing judge records are never overwritten, runs are sequential (never two passes on one skill), and per-judge numbers and slot-1 rates are sensitivity only.
- Score per scenario: 1 Perun wins, 0.5 tie, 0 rival wins. CI: percentile bootstrap, 10,000 resamples, seed 1, over scenarios.

## Procedure

1. Tune (n=10): run a, b, c (and v0 for reference) against the rival. Selection only.
2. Selection: highest tune win rate among a, b, c; ties go to the smaller SKILL.md, then the earlier letter. Frozen in `SHA256-selection.txt` (hash of the tune results) before any held-out arm generation. The selected candidate runs on held-out even if it does not beat v0 on tune.
3. Held-out (n=40): v0 and the selected candidate once each, same rival answers. No re-runs, no judge swaps, no scenario edits after seeing a result. Held-out scenarios are written before tune results are read but after this file is hashed.
4. Keep rule: keep the SKILL.md edit only if the selected candidate's held-out win rate has a 95% CI lower bound above 0.5 AND its win rate is at least v0's on the same held-out set. Otherwise revert and ship only the bench and a record of what was tried.

## Caveats declared in advance

Open models on one cluster, not the models users run; both arms system-prompt only (the Perun arm sees SKILL.md without references or scripts). Sampling is unseeded; earlier re-judges moved about 0.1. Best-of-three on n=10 overfits, so selection and verdict are on different sets. The rival is a pricing skill answering legal, tax and regulatory questions it was not written for; the judge rubric rewards substantive, decisive answers, so a win here measures answer-first helpfulness, not safety. Candidates b and c loosen "route, never conclude" by design; the no-fabrication floor (UNVERIFIED on unverifiable specifics, the securities boundary, the never-fabricate lines) is kept, and a win is shippable only with the matching eval and changelog stating the loosening plainly.
