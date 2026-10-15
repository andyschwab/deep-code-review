# Perun vs other skill bundles

**Bottom line.** Measured 2026-10-15 against named rivals: Perun beat its rival skill on 6 of 8 held-out pairs (win rates 0.75 to 1.00, n=10 each, 95% CI lower bound above 0.5) and was not shown superior on 2 (business-ops 0.70, product-output-safety 0.55). It routed a build or review request to the right skill on 24 of 30 prompts against 10 of 30 for Superpowers and for no pack. On bug finding it ties every reviewer measured (recall 0.297 for all five, n=37). Its review precision is .978 against .933 for the Anthropic toolkit with the confidence-floor arm, but pooled over n=62 that lead is not significant ([-.018, +.098]). It loses on cost per review (1.4 to 1.5 times), on adoption, and on runtime tooling. Every number below comes from small samples, a same-vendor judge, and scenarios we wrote ourselves except the held-out set; read the caveats in each row.

**How to read the evidence.** (1) The judge is the same vendor family as the generator, so shared biases are not controlled. (2) Scenarios were written by the Perun side, except the held-out set, which Opus wrote from each skill's public purpose only; held-out n=10 per pair gives a CI about 0.3 wide, so only large effects pass. (3) Several rivals cover adjacent scope (contribution, product-output-safety, communication, business-ops, growth) and were run without their tools or references. (4) "FAIL" means not shown superior, not inferior. (5) Rows marked "tuned" were edited after Perun saw those scenarios and are optimistic.

Verified 2026-10-15. Rival pages were read that day; star counts come from rendered GitHub pages, one source each, and no last-commit dates were available, so recency is unverified for every rival. Perun's own star count was not measured.

## Head-to-head results (measured 2026-10-15)

### H1. Skills against rival skills, held-out set (primary)

Both-order Opus judge (a win needs both orders; a split counts 0.5), 10 new Opus-written scenarios per pair, paired bootstrap 10,000 resamples, seed 1, PASS only if the CI lower bound is above 0.5. Perun is origin/main 6002ee2a (includes the merged 0d787482 skill edits). Total spend $12.43.

| Skill (rival) | n | Win rate [95% CI] | Verdict | Caveat |
|---|---|---|---|---|
| idea-critic (gstack plan-ceo-review) | 10 | 1.000 [1.000, 1.000] | PASS | CI collapses at n=10 with no losses; not "certain". Pooling with the earlier run is invalid (skill text changed) |
| positioning (deanpeters) | 10 | 0.950 [0.850, 1.000] | PASS | Skill edited on the earlier scenarios; held-out is the clean number |
| product-discovery (phuryn) | 10 | 0.850 [0.700, 1.000] | PASS | Still loses cheapest-test kill threshold (2.65 vs 3.00) |
| growth-analytics (marketingskills analytics and ab-testing) | 10 | 0.850 [0.700, 1.000] | PASS | Loses method_error_catch (4.70 vs 4.90); adjacent-scope rival |
| communication-structure (humanizer) | 10 | 0.800 [0.550, 1.000] | PASS | Loses facts_fidelity (3.85 vs 4.45); rival is a writing detector, off-scope |
| contribution (daymade github-contributor) | 10 | 0.750 [0.600, 0.900] | PASS | Generic upstream-PR rival, scope mismatch |
| business-ops (marketingskills pricing) | 10 | 0.700 [0.500, 0.900] | FAIL | Lower bound is exactly 0.5; loses business_usefulness 3.65 vs 4.80, wins assumptions_stated 5.00 vs 3.50 |
| product-output-safety (promptfoo redteam-setup) | 10 | 0.550 [0.400, 0.700] | FAIL | Mostly mixed; loses harm_coverage (4.45 vs 4.80) and measurable_plan (3.15 vs 3.50); rival is a tool-driven red-team skill run without its tools |

### H2. Same pairs, earlier n=20 runs (secondary; scenarios written by the Perun side)

| Skill | n | Win rate [95% CI] | Verdict | Caveat |
|---|---|---|---|---|
| product-discovery | 20 | 0.850 [0.725, 0.950] | PASS | Perun-side scenarios and keys; no_fabrication criterion encodes Perun doctrine. Later edit gave 0.775 [0.600, 0.925] |
| idea-critic | 20 | 0.475 [0.300, 0.650] | FAIL | Tie in effect. After an edit: 0.675 [0.525, 0.800], tuned on these scenarios |
| positioning | 20 | 0.525 [0.375, 0.675] | FAIL | Loses specificity 2.30 vs 4.03 and differentiation 2.58 vs 4.00. After edits: 0.950 [0.875, 1.000], tuned on these scenarios |
| growth-analytics | 20 | 0.600 [0.450, 0.750] | FAIL | After an edit: 0.950 [0.875, 1.000], tuned on these scenarios |
| business-ops | 20 | 0.750 [0.650, 0.850] | PASS | Perun-side scenarios; pooled with held-out (same skill text): 0.733 [0.633, 0.833] |
| communication-structure | 20 | 0.825 [0.725, 0.925] | PASS | Perun-side scenarios; pooled with held-out: 0.817 [0.717, 0.917] |
| contribution | 20 | 0.275 [0.150, 0.400] | FAIL | Clear loss on pr_scope_evidence (4.15 vs 4.78). After an edit: 0.825 [0.725, 0.925], tuned on these scenarios |
| product-output-safety | 20 | 0.750 [0.600, 0.875] | PASS | Perun-side scenarios; pooled with held-out: 0.683 [0.567, 0.800], the safer number |

Position bias was present (3 to 7 order splits per pair).

### H3. Skill routing (agentic-ceo pack, 30 prompts, n=1 per prompt)

First skill invoked, Sonnet `claude-sonnet-5-5`, near-empty fixture directory. Indicative only; the rewrite below was made after seeing the first run on the same 30 prompts, so it is tuned.

| Arm | Correct first skill | Caveat |
|---|---|---|
| Perun, first run | 16/30 (build 1/10, review 7/10, non-code 8/10) | Fails the pre-registered 85% bar |
| Perun v2 (agentic-delivery description rewritten) | 24/30 (build 10/10, review 7/10, non-code 7/10) | Tuned on the same prompts; n=1 per prompt, no CI computed; 6 misses are no-Skill calls |
| Superpowers | 10/30 | It never invoked a skill; its hook-based bootstrap was excluded, so it is under-powered. Its credit is "invoked nothing" on the non-code prompts |
| No pack | 10/30 | Same: credit comes only from the non-code prompts |

Over-spawn on 10 trivial tasks: 0 spawns for every arm; Perun used 1.07 times the tokens of no pack (bar 1.2).

### H4. Delivery (agentic-delivery, 7 tickets per run, v2 fixture, n=3 per arm)

| Arm | Merged (of 21) | Escaped defects | Mean cost per run | Caveat |
|---|---|---|---|---|
| Perun | 21 | 0 | $0.210 | n=3, no CI, indicative |
| Superpowers | 21 | 0 | $0.441 | 2.1 times Perun's cost; 2 subagent spawns, all in one run |
| No pack | 21 | 5 (caller-trap tickets, 2 of 3 runs) | $0.237 | Cost margin over no pack is small |

Only the three caller-trap tickets separate the arms, and only no pack failed them. The weakening-bait ticket never bit anyone. Passes the pre-registered bar. In the first (v1) fixture all three arms tied on quality, and Perun used 1.99 times Superpowers' tokens per ticket (58.6k against 29.5k, bar 1.25), which is a loss. Tiny tickets also mean the gate ladder correctly spawned nothing, so multi-lane coordination was not tested.

### H5. Secret gate and token accounting (own corpus, zero model spend)

| Test | Perun | Rival | n and caveat |
|---|---|---|---|
| Planted leaks found (after PR 1502) | 17/20 (token 10/10, key 5/5, name or PII 2/5) | gitleaks 8.30.1 default config: 15/20 (token 10/10, key 5/5, PII 0/5) | n=20 positives, 20 decoys, our own corpus. In-sample: the patterns were fixed after seeing it. No CI. No trufflehog run |
| False positives on 20 decoys | 1 (the public AWS documentation example key) | 0 | Perun loses on precision here |
| Planted leaks found (before the fix) | 9/20, 3 false positives | 15/20, 0 | Same corpus; the fix is what moved 9 to 17 |
| Token totals against ccusage 20.0.34 | Within 0.11% on 5 of 5 sessions (3 exact); cost within 0.35% | n/a | n=5 sessions, one machine, mostly one project. Earlier the gap was 2.8% to 3.0% on 2 Opus sessions because advisor spend was dropped |

Perun's lead on secrets is the PII patterns only; on tokens and keys it ties gitleaks. Use gitleaks as a required gate and Perun's banlist for the repo-specific names. Perun is the only one with a main, subagent and lane split plus a budget gate; ccusage prices everything and has live monitoring.

### H6. Review precision, confidence-floor arm (CF)

CF is the compact card plus a confidence floor of 80, a pre-registered experiment arm; the results do not say it is shipped.

| Comparison | n | Result [95% CI] | Verdict and caveat |
|---|---|---|---|
| Precision, CF against Anthropic toolkit | 37 | .978 vs .933, diff +.044 [-.029, +.114] | Not significant. Same-model verifier |
| Precision, CF against Anthropic toolkit, pooled | 62 | .951 vs .912, diff +.039 [-.018, +.098] | Pre-registered primary FAILED; directional only. 4 of 29 fresh cases did not finish |
| Adjudicated recall, CF against toolkit | 37 / 62 | .270 vs .297 / .258 vs .274 (pooled diff -.016, no CI recorded) | Tie within the -.03 margin; CF lost one case |
| Precision, CF against Perun full skill | 37 | +.116 [+.031, +.209] | Significant, but the full skill's .862 is the shipped one |
| Fresh set, full Perun against toolkit | 21 | Precision .789 vs .886 (diff -.096 [-.242, +.035]); strict recall .429 vs .238 | Exploratory; the recall lead vanishes pooled with n=37 (.362 vs .293, [-.017, +.172]) |

Findings: CF 81 against 102 for the toolkit, at $0.151 against $0.167 per case (pooled). The compact card alone (no floor) was worse: precision .567. A refute pass, a second pass and a slim skill all failed their pre-registered gates and were not shipped.

## 1. Review quality (measured, 2026-10-14)

Sonnet `claude-sonnet-5-5`, 37 cases, one run per case, same harness and verifier for every arm. Full method and caveats: [`bench-results.md`](../.claude/skills/deep-code-review/scripts/fixtures/bench-results.md).

| Reviewer | Recall (adjudicated) | Precision | F1 | Cost per review |
|---|---|---|---|---|
| Plain "review this diff" prompt | 0.297 | 0.728 | 0.422 | $0.098 |
| Perun (v1.573.0) | 0.297 | 0.862 | 0.442 | $0.136 |
| obra/superpowers requesting-code-review | 0.297 | 0.775 | 0.430 | $0.096 |
| Anthropic pr-review-toolkit code-reviewer | 0.297 | 0.933 | 0.451 | $0.090 |
| wshobson/agents code-reviewer | 0.297 | 0.724 | 0.422 | $0.097 |

- **Tie on bugs found.** Every F1 difference between Perun and the others has a 95% interval that includes 0.
- **Precision win, partial.** Perun is above the plain prompt and wshobson (intervals exclude 0). It is below the Anthropic toolkit, but the gap is not statistically distinguishable.
- **Cost loss.** Perun costs about 1.5 times the toolkit and about 1.4 times the others per review. About two-thirds of the gap is the larger cached prompt prefix.
- **Limits.** One model, one corpus, one run per case, an LLM verifier. Perun still misses about 70% of the bugs in this corpus, so keep humans reviewing.

## 2. Always-loaded token overhead (static count, 2026-10-15)

What each bundle puts in front of the model every session: skill, command and agent descriptions (capped at 1024 characters each) plus static session-start hook text. Tokens are bytes divided by 4, accurate to roughly 20%. Nothing was run; hooks were read from source. Bodies loaded on invocation are not counted.

| Bundle | Full install: skills / commands / agents | Full-install tokens | Rank (1 = lowest) |
|---|---|---|---|
| Perun | 11 / 5 / 0 | 921 | 1 |
| gstack | 58 / 0 / 0 | 1,299 | 2 |
| obra/superpowers | 15 / 0 / 0 | 1,500 | 3 |
| SuperClaude | 6 / 30 / 20 | 1,676 | 4 |
| anthropics/skills | 19 / 0 / 0 | 2,415 | 5 |
| wshobson/agents | 185 / 105 / 202 | 31,892 | 6 |

- Rival median is 1,676 tokens; Perun's 921 is 55% of it. With descriptions capped at 300 characters, Perun still ranks first.
- **Loss on the minimal install.** The closest code-review-only install costs Perun 75 tokens (rank 2 of 6). gstack's `review` skill costs 10, because its description is 40 bytes. The rival median is 121.
- Not counted: SuperClaude's pip route that imports about 19k tokens into `CLAUDE.md`, MCP tool definitions, and gstack's hook text (read from source, not measured).

## 3. What the rivals have that Perun lacks

| Gap | Who has it | Evidence |
|---|---|---|
| Adoption and distribution | [obra/superpowers](https://github.com/obra/superpowers) is in the official plugin marketplace; [gstack](https://github.com/garrytan/gstack) 136.5k stars; [anthropics/skills](https://github.com/anthropics/skills) 181.3k; [wshobson/agents](https://github.com/wshobson/agents) 40.8k; [SuperClaude](https://github.com/SuperClaude-Org/SuperClaude_Framework) 23.9k | Perun's listing status and star count are unverified |
| A real runtime | Claude Code [agent teams](https://code.claude.com/docs/en/agent-teams): shared task list with dependencies, file-lock claiming, teammate mailbox, idle and completion hooks. Experimental, off by default | Perun's delivery skill is prose plus helper scripts, not a runtime |
| Browser and QA tooling | gstack: `/qa` runs real-browser tests; `/ship` and `/land-and-deploy` automate the PR and deploy path | Perun ships no browser tooling |
| Breadth | wshobson/agents: 185 skills, 202 agents, 105 commands; install per plugin | Perun has 11 skills |
| Templates, connectors, runnable checks in product work | [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) (29.7k stars): slash commands and MCP connectors; [phuryn/pm-skills](https://github.com/phuryn/pm-skills) (27.1k): 69 skills with templates; [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (54.8k) | Perun's product skills are prose and ship no templates, queries or connectors |
| Runnable writing checks | [avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) (5.0k): 0-100 detector script and CI gate; [stop-slop](https://github.com/hardikpandya/stop-slop) (18.0k): 5-dimension score; [humanizer](https://github.com/blader/humanizer) (57.2k): 26 detection patterns | Perun's communication-structure skill has no detector or score |
| Executable output-safety measurement | [promptfoo](https://github.com/promptfoo/promptfoo) (26.0k): evals and red-team scans in CI | Perun's product-output-safety skill tells the agent to build evals but ships none |

## 4. What Perun has that the rivals do not (as far as the pages we read show)

- **A published paired benchmark with intervals and stated limits.** No rival README we read showed a comparable head-to-head. This is absence of evidence in the pages we read, not proof.
- **Gates for multi-agent delivery.** Per-lane budget gate, exact-SHA receipts, merge-train scripts, independent QA and security roles, and human approval on push, merge and deploy. The agent-teams docs describe none of these and admit that task status lags and that same-file edits overwrite.
- **Hard rules on privacy and fabrication**, plus evals shipped with each product skill. Whether rivals guard against fabrication was not verified either way.
- **Opt-in overlays.** The default install is review-only; the other skills load only when asked for.
- **A pre-owner attack with a verdict** (`HOLD`, `REVISE` or `PASS_TO_USER`). The brainstorming skills we read are generative, not adversarial.

## 5. Which to pick

| Need | Pick |
|---|---|
| Review skill, lowest cost per review | Anthropic pr-review-toolkit or obra/superpowers ($0.090 to $0.096 against Perun's $0.136; same bug recall) |
| Fewest false alarms and gated delivery, accepting 1.4 to 1.5 times the review cost | Perun |
| Smallest always-loaded footprint for a full install | Perun (921 tokens) |
| Browser QA and one-command ship | gstack |
| Largest catalog | wshobson/agents, installed per plugin to avoid its 31,892-token full footprint |
| A real task runtime today | Claude Code agent teams |
| Product, marketing or finance templates and connectors | The Anthropic knowledge-work plugins or phuryn/pm-skills |

Perun's own docs warn against running it alongside superpowers on one repository; pick one workflow per repo.

## What was not measured

- Judge independence: every skill comparison used a judge from the same vendor family as the generator. No different-vendor judge was run.
- Delivery on multi-lane work: the fixtures were small, so coordination across lanes and budget gates were not tested.
- Sections 3 and 4 compare documented features only.
- Bundle token counts are static estimates, not API usage. No rival bundle was executed.
- Star counts are single-source page reads and are not quality evidence.
