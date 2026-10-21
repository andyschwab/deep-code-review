---
description: Deliver a change via the gated flow
argument-hint: "[--auto] [change]"
disable-model-invocation: true
---
Load the `agentic-delivery` skill and deliver this change: $ARGUMENTS

If nothing was given, ask for the one-line change request first. Use the smallest sufficient
set of hats, run an independent review before merge, and stop for human approval on push, merge
and deploy.

With `--auto`: write the plan to a file with a line `Grants: push, pr` (add `merge` only if you
are asking the user to approve merging) and ask the user once, in one message, to approve it; if
merge is in the plan, ask them to reply exactly "approve merge", alone. Quote their reply
verbatim, then run `python3 <agentic-delivery>/scripts/plan_gate.py grant --ledger
$TMPDIR/plan-grant.json --plan <plan file> --quote "<reply>"`. A nonzero exit from `grant` means
halt and ask the user. `<agentic-delivery>` is the skill directory:
`.claude/skills/agentic-delivery` in a script install, under the plugin directory in a plugin
install. Then run build, test, independent review and open the PR with no
further prompts. Run `plan_gate.py check <action> --ledger ... --plan ...` before every gated
action (push, pr, merge, force_push, deploy, secrets, spend, delete, external_send,
history_rewrite, settings_edit). Exit 0 = proceed. Exit 3 = park that action and keep going.
Exit 2 (missing, malformed or forged ledger, unreadable plan) = halt the run and ask the user.
Any action not in that list is unrouted and parks by default. Only push, pr and merge can ever
be covered, and merge only when the plan names it and the user's whole reply is exactly
"approve merge" (nothing else in it); the rest always park. If
the plan changes, the grant is void: ask again. At the end, run `plan_gate.py parked --ledger
...` (exit 2 means the ledger was edited: halt and ask) and put every parked action in one
batched ask. The ledger is agent-writable, so this tamper check is advisory only.

`plan_gate.py` is the agent's policy record, not an enforcement point: host permissions and
sandbox stay the boundary, and a denied action stays denied.
