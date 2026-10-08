# Perun

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Perun is a set of written instructions that an AI coding assistant follows to
check software for mistakes the same careful way every time, and to show the
evidence for each problem it reports.**

Perun is the project's name (after the Slavic thunder god of order). This repository is
called `deep-code-review`, after what it does. Its main part is a **skill**: a
text file of instructions the AI assistant reads before it starts work.

## Why it matters

The numbers below come from one test. The assistant (Claude Code, run by
[`scripts/bench_corpus.py`](scripts/bench_corpus.py)) was shown the code change
behind each of 30 real bugs that open-source projects later fixed. It did not
see the fix. The exact test cases stay private so Perun can't be tuned to them;
a [public list](scripts/eval-fixtures/bench/manifest.json) shows which projects
the cases came from. A bug counts as "caught" if the review named it. Every number links to
[the results table](.claude/skills/deep-code-review/references/method-situational.md).

- **Fewer bugs shipped.** With Perun, the assistant caught
  [31% of the bugs](.claude/skills/deep-code-review/references/method-situational.md).
  Asked only to "review this", the same assistant caught
  [21%](.claude/skills/deep-code-review/references/method-situational.md).
  The test is small, so the true gain could be anywhere from
  [0 to 21 points](.claude/skills/deep-code-review/references/method-situational.md).
  Perun still misses most bugs, so keep people reviewing too.
- **Fewer false alarms.**
  [77% of what Perun flagged](.claude/skills/deep-code-review/references/method-situational.md)
  were real problems, against
  [66%](.claude/skills/deep-code-review/references/method-situational.md)
  without it.
- **Lower reading cost.** AI tools charge by the *token* (a piece of a word).
  The instructions the assistant must read before each review shrank by
  [19%](CHANGELOG.md) (release 1.501.0, counted as characters divided by 4).
  A review with Perun still costs more than a plain one:
  [$0.121 per code change reviewed against $0.069](.claude/skills/deep-code-review/references/method-situational.md),
  as reported by the test runner.
- **Safer AI agents.** An *agent* is an AI assistant that can run commands on
  your computer. The installer tells you how to switch on each agent's
  *sandbox* (a fence around what its commands can touch). No number is claimed:
  the effect has not been measured ([host safety](docs/host-safety.md)).

Time saved and money saved have not been measured, so none are claimed. To
estimate them for your team, use the worked formula and the three-step pilot in
[Perun for leaders](docs/for-leaders.md).

## Quick start

You need `git`, a terminal, and an AI coding agent such as Claude Code or
Cursor (the installer lists the others it supports). No terminal? Paste the
skill into any AI chat instead: [getting started](docs/getting-started.md).

1. **Download Perun:**

   ```bash
   git clone --depth 1 https://github.com/remigiusz-antczak/deep-code-review.git
   ```

2. **Install it into your project.** It copies text files only, with no
   network and no admin rights ([`install.sh`](install.sh)):

   ```bash
   deep-code-review/install.sh /path/to/your/project
   ```

3. **Ask your agent to review a real file you care about.** Type this, with
   your file's path at the end. `FILE` tells Perun to review only that file:

   ```
   run a deep code review FILE src/checkout.py
   ```

What step 2 prints (shortened; your version and paths will differ). The last
line names a check you can run to confirm the install works:

```
installed: deep-code-review 1.535.0 (@ 84acfb19) -> your-project/.claude/skills/deep-code-review
safety: Claude Code: OS sandbox is off by default; set sandbox.enabled=true (or run /sandbox) and keep allowUnsandboxedCommands=false. https://code.claude.com/docs/en/sandboxing
Perun installed 1 skill(s) into 3 tool folder(s) of your-project.
Next, run this one command to confirm it works: python3 deep-code-review/scripts/perun_doctor.py your-project
```

The "safety" line is the sandbox setting to switch on for that agent. The "3
tool folders" are where different agents look for skills, so one install works
for several of them.

What step 3 gives you: a list of problems, worst first, on a six-step scale
from Blocker (stops the software working) to Nit (style only). Each problem
names the file and line, the evidence and a fix. A made-up example from the
[example report](docs/example-review-report.md):

```
### F3 - High - CONFIRMED
Inbound webhook accepts unsigned body
- Evidence: routes/hooks.mjs:22 parses JSON; no signature check.
- Fix: verify the signature; bind the account to the verified sender.
```

"CONFIRMED" means the assistant re-checked the problem against the exact code
it reviewed, not just suspected it.

## Who it's for

- **Engineers:** a repeatable review of a file, a branch or a whole project,
  with evidence for every problem.
- **Team leads:** a ranked report you can check, plus a pilot plan
  ([Perun for leaders](docs/for-leaders.md), [team install](docs/team-install.md)).
- **Non-technical teams:** no licence fee ([MIT](LICENSE)), only your AI usage
  cost, and a plain-English summary of risks and decisions
  ([Perun for leaders](docs/for-leaders.md)).

## Safety

Perun is instructions, not a service: your code goes only where your agent
already sends it. Switch on your agent's sandbox and keep human review
([host safety](docs/host-safety.md), [`SECURITY.md`](SECURITY.md)).

## Learn more

- [Perun for leaders](docs/for-leaders.md): a worked story, what each role
  gets, a pilot plan, limits, a glossary and an FAQ.
- [Getting started](docs/getting-started.md): every install option, optional
  skills, updating and removing.
- [Example report](docs/example-review-report.md); the
  [test method](scripts/bench_corpus.py) and
  [cases](scripts/eval-fixtures/bench/) behind the numbers.
- [Technical overview](docs/technical-overview.md),
  [token cost tips](docs/token-cost-tips.md),
  [running many agents](docs/for-fleets.md), [roadmap](docs/roadmap.md).
- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md), rules in
  [`CLAUDE.md`](CLAUDE.md), verified standards in
  [`docs/standards-index.md`](docs/standards-index.md),
  [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md),
  [CI status](https://github.com/remigiusz-antczak/deep-code-review/actions/workflows/ci.yml).

[MIT](LICENSE). Credits and sources: [`docs/standards-index.md`](docs/standards-index.md).
