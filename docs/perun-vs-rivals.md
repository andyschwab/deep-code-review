# Perun vs other skill bundles

**Bottom line.** On finding bugs, Perun ties the other review skills we measured: all five reviewers caught the known bug in the same 11 of 37 cases. Perun's measured edges are fewer false alarms than a plain prompt or wshobson, and the smallest always-loaded footprint of the bundles we counted. It loses on cost per review (about 1.4 to 1.5 times), on adoption (the rivals below show 24k to 181k stars), and on runtime tooling, connectors and templates. Choose Perun for gated delivery, no-fabrication rules and a published benchmark; choose a rival for breadth, a runtime or ready-made templates.

Verified 2026-10-15. Rival pages were read that day; star counts come from rendered GitHub pages, one source each, and no last-commit dates were available, so recency is unverified for every rival. Perun's own star count was not measured.

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

- Perun versus rivals outside code review: no head-to-head exists for delivery, routing, product, safety or writing skills. Sections 3 and 4 compare documented features only.
- Bundle token counts are static estimates, not API usage. No rival bundle was executed.
- Star counts are single-source page reads and are not quality evidence.
