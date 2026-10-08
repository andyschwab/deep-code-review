# Perun for leaders

**Bottom line:** Perun is a free checklist that makes an AI coding assistant review software the same careful way every time. It finds more real bugs than a plain "review this" request, at about 1.75 times the usage cost for one pass and 3.5 times for the two-pass setting. Running the plain assistant twice recovers part of the gain more cheaply ([source](../.claude/skills/deep-code-review/references/method-situational.md)). The evidence is one test, so treat the gain as probable, not proved. A small pilot will tell you whether it pays off for your team.

## What Perun does

It is a set of plain-text instructions your engineers' AI assistant reads before reviewing a change. Every problem it reports names the exact file and line, ranks how serious it is, and says how to fix it. What it cannot confirm, it labels `unverified` instead of guessing. There is no server and no account. See the [sample report](example-review-report.md).

## What changes for a team

- Reviews follow one method instead of the assistant's mood that day. Source: [README](../README.md#the-story-one-change-five-steps).
- Each review costs more model usage: one Perun pass costs about $0.121 per case against $0.069 for a plain review (about 1.75 times); two merged passes cost $0.239 (about 3.5 times). Source: [measured table](../.claude/skills/deep-code-review/references/method-situational.md).
- Engineers still decide what to fix. Perun reports; it does not change code on its own.

## Measured numbers

All numbers come from one test of 30 held-out real bug fixes, 3 runs per setup, described in the [measured table](../.claude/skills/deep-code-review/references/method-situational.md). Each line below cites its source.

- Bugs found: plain assistant 21%, Perun one pass 31%, Perun two merged passes 41%, plain assistant run twice 36% (about $0.132 per case). The 41% costs $0.239 per case. Source: [measured table](../.claude/skills/deep-code-review/references/method-situational.md).
- Share of flagged issues that were real: plain 66%, Perun 77%. Source: [measured table](../.claude/skills/deep-code-review/references/method-situational.md).
- Gain over plain: +0.10, but the margin of error runs from 0.00 to +0.21, so "probably better". Source: [measured table](../.claude/skills/deep-code-review/references/method-situational.md).
- Other AI models: unmeasured for review recall, so do not assume the gain carries over.
- Time saved, money saved, customer count: unmeasured. Nobody has measured these yet.

## Risks and controls

- **An agent running commands on a machine.** Control: run it inside the operating-system sandbox where the tool offers one; per-tool status is in [host safety](host-safety.md). Some tools have none, so use a container or virtual machine for those.
- **Private data leaking into code, commits or reports.** Control: a privacy gate blocks names, emails and secrets before anything is committed. See [technical overview](technical-overview.md).
- **Changes published without anyone looking.** Control: Perun never pushes, merges or opens requests by itself; a human does the last step. See the contribution rules in [SKILL.md](../.claude/skills/contribution/SKILL.md).
- **Overconfidence.** Perun misses most bugs. Keep your normal human review.

## Three-step pilot

1. **Pick one team and one repository.** Have an engineer install Perun in review-only mode and turn the sandbox on, following [team install](team-install.md).
2. **Run it on every change for a few weeks, alongside normal review.** Record how many real problems it found that people missed, and the extra usage cost. Both are unmeasured for your code until you do this.
3. **Decide with your own numbers.** Keep it if the problems found are worth more than the extra cost; drop it if not. Cost tips: [token cost tips](token-cost-tips.md).
