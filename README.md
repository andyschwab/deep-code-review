# Perun

[![gates](https://github.com/remigiusz-antczak/deep-code-review/actions/workflows/ci.yml/badge.svg)](https://github.com/remigiusz-antczak/deep-code-review/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Perun is a free, plain-text checklist that makes an AI coding assistant review
software the same careful way every time, and show exactly what it checked.**

Perun is the project; `deep-code-review` is this repository and its main
**skill** (a text file of instructions the AI assistant reads before it starts).

## Why it matters

- **Fewer bugs shipped.** In a test on 30 real bug fixes from open-source
  projects, one Perun review caught 31% of the hidden bugs. The same assistant
  asked to "review this" caught 21%. Two Perun reviews merged caught 41%
  ([measured table](.claude/skills/deep-code-review/references/method-situational.md)).
  The gain is probable, not proved: +10 points, with a 95% interval of 0 to +21
  (same table). It still misses most bugs, so keep human review.
- **Fewer false alarms.** 77% of the problems Perun flagged were real, against
  66% for the plain assistant
  ([same table](.claude/skills/deep-code-review/references/method-situational.md)).
- **Safer AI agents.** An *agent* is an AI assistant that can run commands on a
  computer. When you install Perun, it prints, for each agent tool, the
  *sandbox* setting to turn on (a sandbox is a fence that limits what the
  agent's commands can touch) and runs a quick sandbox check
  ([host safety](docs/host-safety.md)). The effect on incidents has not been
  measured.
- **Its own reading cost, cut 19%.** AI tools bill by the *token*, roughly a word
  fragment. The text an agent must read before every review fell from 28,589 to
  23,173 tokens ([`CHANGELOG.md`](CHANGELOG.md), entry 1.501.0). A Perun review
  still costs more than a plain one: $0.121 per test case against $0.069. The
  plain assistant asked twice cost $0.132 and caught 36%
  ([same table](.claude/skills/deep-code-review/references/method-situational.md)).

Time saved, money saved and customer counts have not been measured, so none are
claimed.

## Start in 60 seconds

You need `git`, a terminal, and an AI coding agent such as Claude Code, Cursor,
Codex, Copilot, Gemini or Aider.

1. **Download Perun:**

   ```bash
   git clone --depth 1 https://github.com/remigiusz-antczak/deep-code-review.git
   ```

2. **Install it into your project** (copies text files and needs no admin
   rights):

   ```bash
   deep-code-review/install.sh /path/to/your/project
   ```

3. **Ask your agent** in plain words: `run a deep code review FILE <a file in your project>`.
   Pick a real file you care about.

What step 2 prints (trimmed; your version, commit and paths will differ):

```
installed: deep-code-review 1.535.0 (@ 84acfb19) -> your-project/.claude/skills/deep-code-review
safety: Claude Code: OS sandbox is off by default; set sandbox.enabled=true (or run /sandbox) and keep allowUnsandboxedCommands=false. https://code.claude.com/docs/en/sandboxing
run it:  tell your agent in plain words: run a deep code review FILE <a file in your project>
Perun installed 1 skill(s) into 3 tool folder(s) of your-project.
Next, run this one command to confirm it works: python3 deep-code-review/scripts/perun_doctor.py your-project
```

What step 3 gives you: a list ranked from Blocker down to Nit, where each
problem names the file and line, the evidence and a fix. One finding looks like
this (a fictional sample from the [example report](docs/example-review-report.md)):

```
### F3 - High - CONFIRMED
Inbound webhook accepts unsigned body
- Evidence: routes/hooks.mjs:22 parses JSON; no signature check.
- Fix: verify the signature; bind the account to the verified sender.
```

Checksums, pinning a release, other agents, no-terminal use, optional skills,
updating and removing: [getting started](docs/getting-started.md). Whole team on
Claude Code: [team install](docs/team-install.md).

## Who it's for

- **Engineers:** a repeatable review of a file, a branch or a whole repository,
  with evidence for every problem, in any language.
- **Team leads:** a severity-ranked report plus a traffic-light summary, so
  "reviewed" has a meaning you can check ([example report](docs/example-review-report.md)).
- **Non-technical teams (finance, marketing, product, leadership):** no licence
  fee, only AI usage cost, and a plain-English summary of risks and the
  decisions that need an owner ([Perun for leaders](docs/for-leaders.md)).

## Safety

Perun is text files: it sends nothing itself, and your code goes only where your
agent already sends it. Turn on your agent's sandbox and keep human review,
because Perun misses most bugs ([host safety](docs/host-safety.md), [`SECURITY.md`](SECURITY.md)).

## Learn more

- [Perun for leaders](docs/for-leaders.md): for decision makers, with a
  worked story, what each role gets, limits, a glossary and an FAQ.
- [Getting started](docs/getting-started.md): every install option, the
  optional skills, updating and removing.
- [Example report](docs/example-review-report.md) and the
  [benchmark](scripts/eval-fixtures/bench/) behind the numbers above.
- [Technical overview](docs/technical-overview.md),
  [token cost tips](docs/token-cost-tips.md), [running many agents](docs/for-fleets.md),
  [roadmap](docs/roadmap.md).
- Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md), rules in
  [`CLAUDE.md`](CLAUDE.md), verified standards in
  [`docs/standards-index.md`](docs/standards-index.md),
  [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

[MIT](LICENSE). Inspired by open coding-agent setups (including
[`nickmaglowsch/claude-setup`](https://github.com/nickmaglowsch/claude-setup))
and grounded in the public standards listed in
[`docs/standards-index.md`](docs/standards-index.md).
