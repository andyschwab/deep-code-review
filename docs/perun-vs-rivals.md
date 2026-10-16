# Perun vs other skill bundles

**Bottom line.** Mixed, and the strongest claim is narrow. (1) Skills: measured 2026-10-15, Perun beat its rival skill on 6 of 8 held-out pairs (win rates 0.75 to 1.00, n=10 each, 95% CI lower bound above 0.5) and was not shown superior on 2 (business-ops 0.70, product-output-safety 0.55). Routing: 24 of 30 prompts correct against 10 of 30 for Superpowers and for no pack, but that is a re-run after tuning on the same 30 prompts (the first run scored 16 of 30 and missed its 85% bar), n=1 per prompt, and Superpowers ran without its hooks. (2) Code review, patch-only, 43 public cases, measured 2026-10-16: Perun's small-diff method trades recall for precision and ties on F1. Against the Anthropic pr-review-toolkit its precision is .780 against .644 (+.137, CI [+.032, +.247], significant) and its recall is .488 against .628 (-.140, CI [-.256, -.047], significantly worse). Three variants meant to recover the recall were tried on a tuning half; the best one failed on the held-out half (n=22, F1 -.036, CI [-.194, +.095]). On the earlier 37-case run every reviewer tied on bug recall (.297, n=37); the earlier precision lead (.951 against .912 pooled, n=62, CI [-.018, +.098]) was not significant, so treat the 2026-10-16 run as the current precision number and do not read Perun as finding more bugs. (3) Host safety: the destructive-command guard (shipped in 1.580.0) blocked 30 of 32 dangerous command strings against 19 of 32 for claude-code-safety-net and 13 of 32 for hooks-mastery, with 0 of 30 false positives (Perun was at 11 of 32 before the guard). It is a best-effort string check, not a security boundary: three adversarial reviews found residual bypasses (interpreter APIs, IFS and brace tricks, exotic wrappers), rated medium, and the OS sandbox is the boundary. (4) Test quality: Perun's old vacuous-test gate caught 2 of 20 vacuous tests. The advisory static pass shipped in 1.581.0 catches 5 of 20 with 0 of 20 false positives on a separate held-out set, so it is not scored on the same tests as the rivals (eslint-plugin-jest 5 of 20, ruff 3 of 20, mutation testing 17 of 20 lenient and 12 strict, on the earlier corpus); any ranking is indicative, and the pass is far behind mutation testing and missed its own preregistered recall bar of 12 of 20. mutation_changed.py (1.581.0, measured on 1.582.0) runs the project's installed mutation tool on changed lines, the same technique family as mutation testing, but the 17 of 20 was a whole-suite, lenient score that included JavaScript and does not carry over to this wrapper. On a separate held-out set of 20 vacuous and 20 genuine Python tests, unseen when the fix was made, it flagged 18 of 20 vacuous tests (90%; 14 of 20 from surviving mutants alone, the other 4 as NOT_COVERED), but its preregistered noise bar failed: 7 of 20 genuine tests showed at least one equivalent mutant (2 of 20 counting only cases where every flagged mutant is equivalent), plus 55 surviving mutants in 12 thin genuine tests. That is why it stays advisory; the set differs from the 17 of 20 set, so the two are not compared. Python (mutmut 3.8) only; JavaScript/Stryker is unverified. Perun also costs more per review than the rivals with the earlier full method (1.25 to 1.42 times; the confidence-floor method costs about the same as the toolkit, $.134 against $.142 per case), and it trails on adoption and runtime tooling. (5) Install (1.583.0): 0.2 to 0.6 s, 3 typed commands, doctor passes on a fresh install and uninstall left 0 files, but these 1.583.0 doctor, uninstall and backup results are release-check claims, not part of the 1.582.0 bench tables, and superpowers still covers 15 to 16 hosts per its docs against Perun's 4 native hosts and has more adoption (H10). Every number below comes from small samples, a same-vendor judge, and scenarios we wrote ourselves except the held-out set; read the caveats in each row.

**How to read the evidence.** (1) The judge is the same vendor family as the generator, so shared biases are not controlled. (2) Scenarios were written by the Perun side, except the held-out set, which Opus wrote from each skill's public purpose only; held-out n=10 per pair gives a CI about 0.3 wide, so only large effects pass. (3) Several rivals cover adjacent scope (contribution, product-output-safety, communication, business-ops, growth) and were run without their tools or references. (4) "FAIL" means not shown superior, not inferior. (5) Rows marked "tuned" were edited after Perun saw those scenarios and are optimistic.

Verified 2026-10-15 (rival pages, skill pairs, routing, delivery, secrets) and 2026-10-16 (H7 to H9). Rival pages were read on the 15th; star counts come from rendered GitHub pages, one source each, and no last-commit dates were available, so recency is unverified for every rival. Perun's own star count was not measured.

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

### H7. Review, patch-only head-to-head, small-diff method against Anthropic toolkit (2026-10-16)

CF is Perun's small-diff method (the compact card with the confidence floor); TK is the Anthropic pr-review-toolkit code-reviewer. 43 public cases committed under `scripts/eval-fixtures/bench/train`, reviewer sees `change.patch` only, Sonnet `claude-sonnet-5-5` as reviewer, Opus `claude-opus-5-5` as blind verifier, one run per case, no cases dropped, spend $3.50. Precision is verified good findings over findings; recall is adjudicated bugs credited over bugs. These levels are not comparable with the 37-case tables above (different corpus, patch-only, different verifier).

| Metric | CF | TK | Difference [95% CI] | Verdict |
|---|---|---|---|---|
| Findings | 41 (32 good) | 73 (47 good) | | |
| Precision (n=43 cases) | .780 | .644 | +.137 [+.032, +.247] | Perun significantly better |
| Adjudicated recall (n=43 cases, 43 bugs) | .488 (21 credited) | .628 (27 credited) | -.140 [-.256, -.047] | Perun significantly worse |

The pre-registered primary (precision) was met; the secondary (recall not worse) was not, so the pre-registered verdict is FAIL. Plainly: Perun trades recall for precision. It raises more trustworthy findings per finding, but surfaces fewer of the real bugs.

Recall-recovery attempt (CF60, CFDIFF, CFHUNT; chosen on a 21-case tune half, then scored on the other 22 cases, spend $6.38). The chosen variant CFHUNT against TK on that held-out half:

| Metric (n=22) | CFHUNT | TK | Difference [95% CI] | Verdict |
|---|---|---|---|---|
| Precision | .789 | .636 | +.153 [-.021, +.359] | Not significant |
| Recall | .455 | .591 | -.136 [-.273, .000] | Not shown worse; lower bound is exactly 0 |
| F1 | .577 | .613 | -.036 [-.194, +.095] | Tie; interval includes 0 |

No variant recovered the recall (pre-registered PASS false), so this result gives no reason to adopt any of them. On this half the original CF scored F1 .526 against TK's .613 (-.087, CI [-.243, +.037]). Result: a tie on F1, with a different trade-off. One model, one run per case, same-vendor verifier, 43 cases from public repositories; a half of 22 gives wide intervals.

### H8. Host safety, destructive-command guard (shipped 1.580.0)

32 dangerous command strings and 30 benign ones, run through each tool's check; blocked means refused before execution. Intervals are Wilson 95%, computed here from the counts.

| Tool | Blocked of 32 dangerous [95% CI] | False positives of 30 benign |
|---|---|---|
| Perun destructive guard (1.580.0) | 30 [.799, .983] | 0 [0, .114] |
| claude-code-safety-net | 19 [.423, .745] | not reported |
| hooks-mastery | 13 [.255, .577] | not reported |
| Perun before the guard | 11 [.204, .517] | not reported |

The guard is a best-effort string check, not a security boundary. Three adversarial reviews found residual bypasses (interpreter APIs such as `subprocess` and `exec`, IFS and brace-expansion tricks, exotic wrappers), rated medium. The OS sandbox is the boundary; keep it on. A 32-string corpus is small, so the lead over the rivals is indicative.

### H9. Test quality, vacuous-test detection

A 40-test corpus with 20 vacuous tests (the other 20 are not vacuous). Counts are vacuous tests caught; intervals are Wilson 95%, computed here.

| Detector | Caught of 20 [95% CI] | False positives of 20 |
|---|---|---|
| Mutation testing | 17 lenient, 12 strict [.640, .948 for 17] | 2 |
| eslint-plugin-jest | 5 [.112, .469] | 2 |
| ruff | 3 [.052, .360] | 1 |
| Perun vacuous-test gate (old) | 2 [.028, .301] | not reported |

Perun loses here: the old gate caught about as few as the cheapest linters, and mutation testing is far ahead.

Shipped in 1.581.0:

- An advisory static vacuous-test pass. On a fresh held-out set it caught 5 of 20 (Python 3 of 10, JavaScript 2 of 10) with 0 of 20 false positives, and it produced 0.22 false positives per 100 tests on the suites of three popular open-source projects (2277 tests; counting assertion-only-in-except tests as false positives). The table above scores the other detectors on the earlier 40-test corpus, not on this held-out set, so the sets differ and any ranking is indicative: 5 of 20 is the same count as eslint-plugin-jest (5 of 20, 2 false positives), above ruff (3 of 20, 1 false positive) and far below mutation testing (17 of 20 lenient, 12 strict, 2 false positives). It missed its preregistered recall bar (12 of 20). The 0.22 figure comes from the same suites used to tune out false positives, so it is a development number, not an independent estimate.
- `mutation_changed.py`, which runs the project's installed mutation tool on changed lines (mutmut 3.x verified; Stryker unverified). It is the same technique family as the mutation-testing row, but that row's 17 of 20 was a whole-suite, lenient score that included JavaScript and does not carry over to this wrapper, and the sets differ, so no direct comparison is made. Held-out measurement of 1.582.0 (Python only, mutmut 3.8, 20 vacuous and 20 genuine tests unseen when the fix was made, zero model calls): recall 18 of 20 (90%), of which 14 of 20 come from surviving mutants alone and the other 4 are NOT_COVERED; 2 vacuous tests were missed (a tuple-assert that still executes the code, so any raising mutant is killed, and expected values generated by the function itself at import). Noise: 7 of 20 genuine cases show at least one equivalent mutant (2 of 20 counting equivalent-only cases, where every flagged mutant is equivalent), plus 55 surviving mutants in 12 thin genuine tests; 6 of 20 genuine cases had no finding. The preregistered bar (at most 10% genuine cases with an equivalent mutant) failed, so the preregistered verdict is FAIL and the check stays advisory. JavaScript/Stryker is unverified.

### H10. Install and update (1.583.0; timings measured on 1.582.0, host and uninstall fixes from the 1.583.0 release checks)

Zero model spend. Timings and file counts come from one run per cell of the install bench on 1.582.0 (3 project fixtures, default, `--minimal` and `--full` modes); differences under about 0.05 s are noise. The rival columns are README reads only: no rival installer was run.

| Measure | Perun 1.583.0 | obra/superpowers | Caveat |
|---|---|---|---|
| Install time | 0.2 to 0.6 s (0.21 minimal, 0.37 default, 0.59 full, median) | Not reported | Timed on 1.582.0 with the network blocked; the clone itself needs network |
| Typed commands | 3 (clone, install, doctor); 2 via the plugin | 2 on Claude Code, 1 via the official marketplace; 1 command or UI click on about 15 other hosts | Rival counts are from its README |
| Native install hosts | Claude Code, Codex, Gemini CLI, Copilot CLI | 15 to 16 per its docs | See the next paragraph for how each was checked |
| Doctor on a fresh install | Passes | No equivalent check documented | On 1.582.0 doctor exited 1 on 9 of 9 fresh installs (WARN only); this is the fixed behavior |
| Re-run and update | Backs up only when content differs; backups are never pruned | Not documented | On 1.582.0 every re-run added a full backup (4.2 to 19.9 MB per run); unpruned backups still accumulate whenever content changes |
| Uninstall | Leaves 0 Perun files; deletes only unmodified shipped files; restores the pre-install copy | Not documented for any host | On 1.582.0 uninstall left 327 (minimal), 979 (default) and 1,690 (full) files behind, mostly backups (bench-local/install results.json, 9 cells) |

How the four native hosts were checked: Claude Code is the existing plugin. Codex was smoke-tested with an isolated `CODEX_HOME` and listed 11 of 11 skills. The Gemini CLI manifest was validated against its documentation only; no Gemini CLI install was run. Copilot CLI is expected to read the existing Claude marketplace file, per its documentation; no Copilot CLI install was run.

Three safety reviews of the uninstall and backup changes found and closed 4 data-loss bugs before release. That is a count of defects found by our own reviews, not a guarantee that none remain.

Perun still loses on reach and adoption: obra/superpowers covers 15 to 16 hosts per its docs with one native command each, against Perun's 4, and it has far more adoption. The 1.583.0 work narrows the gap on Claude Code, Codex, Gemini CLI and Copilot CLI only; the other hosts superpowers lists have no Perun native install.

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
| Native install reach | obra/superpowers: one native command or UI click on 15 to 16 hosts per its docs | Perun has native install on 4 (Claude Code, Codex, Gemini CLI, Copilot CLI); two of the four are untested on a real install (see H10) |
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
| Fewest false alarms per finding and gated delivery, accepting fewer bugs found than the toolkit (recall .488 against .628, patch-only) | Perun small-diff method |
| Most bugs found per review (recall .628 against .488, patch-only) | Anthropic pr-review-toolkit |
| Blocking common destructive shell mistakes (not a security boundary) | Perun destructive guard (30 of 32 strings); keep the OS sandbox on |
| Catching vacuous tests | Mutation testing (17 of 20), not Perun's gate (2 of 20) |
| Smallest always-loaded footprint for a full install | Perun (921 tokens) |
| Native install on the most hosts | obra/superpowers (15 to 16 hosts per its docs against Perun's 4) |
| Sub-second, project-local install with a self-check and a clean, dry-run-first uninstall | Perun (0.2 to 0.6 s; uninstall left 0 files in the 1.583.0 release checks) |
| Browser QA and one-command ship | gstack |
| Largest catalog | wshobson/agents, installed per plugin to avoid its 31,892-token full footprint |
| A real task runtime today | Claude Code agent teams |
| Product, marketing or finance templates and connectors | The Anthropic knowledge-work plugins or phuryn/pm-skills |

Perun's own docs warn against running it alongside superpowers on one repository; pick one workflow per repo.

## What was not measured

- Judge independence: every skill comparison used a judge from the same vendor family as the generator. No different-vendor judge was run.
- Destructive guard: 32-string corpus; no real-agent transcripts, and residual bypasses are known.
- Vacuous-test detection: one 40-test corpus; the static pass was measured on one 20-test held-out set; `mutation_changed.py` was measured on one 40-test Python-only held-out set (20 vacuous, 20 genuine), with JavaScript unmeasured.
- Install: no rival installer was run; the 1.583.0 uninstall, backup and doctor results are release-check claims, not part of the 1.582.0 bench tables; the Gemini CLI and Copilot CLI native installs were not run on a real host.
- Delivery on multi-lane work: the fixtures were small, so coordination across lanes and budget gates were not tested.
- Sections 3 and 4 compare documented features only.
- Bundle token counts are static estimates, not API usage. No rival bundle was executed.
- Star counts are single-source page reads and are not quality evidence.
